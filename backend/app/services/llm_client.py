"""LLM client wrapper for Google Gemini.

Hardened for production-adjacent use:
- Pydantic schema validation on the model output (structured-output contract).
- Retry with exponential backoff on transient failures (network, rate limit,
  malformed JSON).
- Deterministic generation (temperature=0) for reproducible extractions.
- Explicit exception taxonomy so callers can distinguish
  provider failures from schema-contract violations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

_client = None

# ── Tunables ─────────────────────────────────────────────────────────────
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 1.0  # 1s, 2s, 4s
GENERATION_TEMPERATURE = 0.0


# ── Exceptions ───────────────────────────────────────────────────────────

class LLMError(Exception):
    """Base class for LLM-related failures."""


class LLMProviderError(LLMError):
    """Raised when the upstream provider (Gemini) fails after retries."""


class LLMSchemaError(LLMError):
    """Raised when the model output cannot be parsed or fails schema validation."""


# ── Structured-output schemas ────────────────────────────────────────────

class LLMLineItem(BaseModel):
    description: str
    amount: float


class ExtractionLLMResponse(BaseModel):
    """Contract for the JSON the LLM must return on extraction.

    Every field is optional except those that the validator enforces.
    `readability_score` is bounded to [0, 1] — anything outside that
    range fails validation and triggers a retry.
    """

    patient_name: str | None = None
    doctor_name: str | None = None
    doctor_registration: str | None = None
    hospital_name: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[str] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)
    line_items: list[LLMLineItem] = Field(default_factory=list)
    total_amount: float | None = None
    date: str | None = None
    readability_score: float = Field(default=0.8, ge=0.0, le=1.0)


class QualityLLMResponse(BaseModel):
    readability_score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    document_type_detected: str = "UNKNOWN"


# ── Internals ────────────────────────────────────────────────────────────

def _get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise LLMProviderError("GEMINI_API_KEY not set")
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _parse_and_validate(raw_text: str, schema: type[BaseModel]) -> BaseModel:
    """Parse JSON + validate against schema, raising LLMSchemaError on failure."""
    try:
        data = json.loads(_strip_json_fences(raw_text))
    except json.JSONDecodeError as e:
        raise LLMSchemaError(f"Model output is not valid JSON: {e}") from e

    try:
        return schema.model_validate(data)
    except ValidationError as e:
        raise LLMSchemaError(
            f"Model output failed {schema.__name__} schema validation: {e}"
        ) from e


async def _with_retry(fn: Callable[[], Any]) -> Any:
    """Run `fn` with exponential backoff on transient failures.

    LLMSchemaError is treated as retryable — the model sometimes returns
    malformed JSON on first try and fixes itself with the same prompt.
    """
    last_err: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return fn()
        except (LLMSchemaError, Exception) as e:  # noqa: BLE001 — retry on anything transient
            last_err = e
            if attempt < MAX_ATTEMPTS - 1:
                delay = BASE_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs.",
                    attempt + 1, MAX_ATTEMPTS, e, delay,
                )
                await asyncio.sleep(delay)
    # Out of attempts
    if isinstance(last_err, LLMSchemaError):
        raise last_err
    raise LLMProviderError(f"LLM provider failed after {MAX_ATTEMPTS} attempts: {last_err}") from last_err


# ── Public API ───────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a medical document extraction agent for an Indian health insurance company.
Extract structured information from this {document_type}.

Return ONLY valid JSON with these fields (use null for unreadable fields):
{{
    "patient_name": "string or null",
    "doctor_name": "string or null",
    "doctor_registration": "string or null",
    "hospital_name": "string or null",
    "diagnosis": "string or null",
    "treatment": "string or null",
    "medicines": ["list of medicine names"],
    "tests_ordered": ["list of test names"],
    "line_items": [{{"description": "string", "amount": number}}],
    "total_amount": number or null,
    "date": "YYYY-MM-DD or null",
    "readability_score": 0.0 to 1.0
}}"""


async def extract_document_data(
    image_bytes: bytes | None = None,
    image_path: str | None = None,
    document_type: str = "medical document",
    extraction_prompt: str | None = None,
) -> dict[str, Any]:
    """Extract structured data from a document image using Gemini vision.

    Returns a dict matching `ExtractionLLMResponse`. Raises:
      - LLMProviderError: the provider kept failing after retries.
      - LLMSchemaError:   the provider returned data that doesn't match the schema.
    """
    client = _get_client()
    prompt = extraction_prompt or EXTRACTION_PROMPT.format(document_type=document_type)

    def _call() -> dict[str, Any]:
        contents: list[Any] = [prompt]
        if image_bytes:
            from google.genai import types
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        elif image_path:
            with open(image_path, "rb") as f:
                from google.genai import types
                contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

        t0 = time.time()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config={"temperature": GENERATION_TEMPERATURE},
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info("LLM extraction call took %dms", elapsed_ms)

        validated = _parse_and_validate(response.text, ExtractionLLMResponse)
        return validated.model_dump()

    return await _with_retry(_call)


QUALITY_PROMPT = """Analyze this document image for readability.
Return ONLY valid JSON:
{
    "readability_score": 0.0 to 1.0 (0=completely unreadable, 1=perfectly clear),
    "issues": ["list of issues like blur, darkness, rotation, etc."],
    "document_type_detected": "PRESCRIPTION or HOSPITAL_BILL or LAB_REPORT or PHARMACY_BILL or UNKNOWN"
}"""


async def assess_document_quality(
    image_bytes: bytes | None = None,
    image_path: str | None = None,
) -> dict[str, Any]:
    """Assess document readability using Gemini vision."""
    client = _get_client()

    def _call() -> dict[str, Any]:
        contents: list[Any] = [QUALITY_PROMPT]
        if image_bytes:
            from google.genai import types
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        elif image_path:
            with open(image_path, "rb") as f:
                from google.genai import types
                contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config={"temperature": GENERATION_TEMPERATURE},
        )
        validated = _parse_and_validate(response.text, QualityLLMResponse)
        return validated.model_dump()

    return await _with_retry(_call)
