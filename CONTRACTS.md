# Component Contracts

Formal input/output/error/invariant contracts for every component in the pipeline. These are the promises each component makes to its callers and the assumptions it may make about its inputs.

---

## Orchestrator (`app/agents/orchestrator.py`)

**Input:** `ClaimSubmission`  
**Output:** `ClaimDecision`  
**Errors raised:** None — the orchestrator is the top-level failure boundary and must always return a `ClaimDecision`.

**Invariants:**
- `ClaimDecision.confidence_score` is always in `[0.30, 1.0]`.
- If `document_errors` is non-empty and `decision is None`, the document gate hard-stopped the pipeline. The caller should display document errors and request re-upload, not treat this as a rejection.
- If `simulate_component_failure=True`, at least one `TraceStep` with `status="ERROR"` will be present and `confidence_score ≤ 0.80`.
- `ClaimDecision.trace.steps` records every check run, in the order it ran. The timestamps are monotonically increasing.
- Every stage failure debits exactly `−0.20` confidence. A single failed stage cannot reduce confidence below the floor of `0.30`.

**Contract violations the orchestrator defends against:**
- Document gate raises an unhandled exception → caught, logged as ERROR trace step, pipeline continues with empty extraction.
- Extraction raises → caught, `_fallback_extraction` produces a minimal document from the `ClaimSubmission` fields; adjudication still runs.
- Adjudication raises → caught, decision defaults to `MANUAL_REVIEW` with `confidence ≤ 0.60`.

---

## Document Gate (`app/agents/document_gate.py`)

**Input:** `list[DocumentInput]`, `claim_category: ClaimCategory`, `member_id: str`  
**Output:** `DocumentGateResult(passed: bool, errors: list[DocumentError])`  
**Errors raised:** None — all failures expressed as `DocumentError` entries.

**Check order and semantics:**

| # | Check | Failure type | Stops pipeline |
|---|-------|-------------|----------------|
| 1 | Type completeness | `MISSING_DOCUMENT` | Yes |
| 2 | Document quality | `UNREADABLE_DOCUMENT` | Yes |
| 3 | Name consistency | `MISMATCHED_PATIENT_NAME` | Yes |

**Invariants:**
- If `passed=False`, `errors` is non-empty (at least one entry).
- If `passed=True`, `errors` is empty.
- `DocumentError.message` is always specific and actionable: it names the missing document type or the conflicting names, never a generic string.
- The gate does **not** evaluate policy rules. It only validates structural and quality properties of the submitted documents.
- A single `UNREADABLE` document fails the gate even if all other documents are valid. The error message asks for re-upload, not rejection of the claim.

---

## Extraction Agent (`app/agents/extraction.py`)

**Input:** `list[DocumentInput]`  
**Output:** `list[ExtractedDocument]`  
**Errors raised:** `ExtractionError` (caught by Orchestrator)

**Dual-path contract:**
- If `DocumentInput.content` is provided: content is mapped directly into `ExtractedDocument` fields. No LLM call is made. Confidence for each field defaults to `1.0` if the field is present and non-null, `0.5` if absent/null.
- If `DocumentInput.content` is absent: `LLMClient.extract_document_data` is called with the file bytes and a document-type-specific prompt. Confidence is derived from the LLM's `readability_score`.

**Invariants:**
- One `ExtractedDocument` is produced per input `DocumentInput`.
- `ExtractedDocument.source_document_id` matches the corresponding `DocumentInput.file_id`.
- Fields that cannot be extracted are `None`; lists that cannot be extracted are `[]`.
- `extraction_confidence` is always in `[0.0, 1.0]`. A score below `0.70` triggers a `−0.05` confidence debit per low-confidence field in the orchestrator.
- The agent never modifies the `DocumentInput` objects it receives.

---

## Adjudication Agent (`app/agents/adjudication.py`)

**Input:** `list[ExtractedDocument]`, `ClaimSubmission`, `PolicyTerms`, `list[FraudSignal]`  
**Output:** `AdjudicationResult(decision, approved_amount, rejection_reasons, line_item_decisions, amount_breakdown, notes)`  
**Errors raised:** `AdjudicationError` (caught by Orchestrator)

**Rule ordering (ordering is load-bearing):**

| Order | Rule | Outcome on failure |
|-------|------|--------------------|
| 1 | Exclusion check | `REJECTED` or `PARTIAL` |
| 2 | Waiting period | `REJECTED` |
| 3 | Pre-authorization | `REJECTED` |
| 4 | Per-claim limit | `REJECTED` |
| 5 | Annual OPD limit | `REJECTED` or amount capped |
| 6 | Fraud review | `MANUAL_REVIEW` |
| 7 | Amount calculation | (produces `approved_amount`) |

**Amount calculation invariant (step 7):**
```
approved = claimed_amount
           → drop excluded line items (PARTIAL path)
           → × (1 − network_discount) if network hospital
           → × (1 − copay_percent)
           → min(approved, per_claim_limit)
           → min(approved, remaining_annual_limit)
```
Network discount is always applied **before** copay. This is not negotiable — the policy terms define it in this order.

**Invariants:**
- If `decision = REJECTED`, `approved_amount = 0` and `rejection_reasons` is non-empty.
- If `decision = APPROVED` or `PARTIAL`, `approved_amount > 0`.
- If `decision = PARTIAL`, at least one `LineItemDecision` has `status = "REJECTED"` and one has `status = "APPROVED"`.
- `amount_breakdown` is populated if and only if `decision in {APPROVED, PARTIAL}`.
- The per-claim limit check uses `max(per_claim_limit, category_sub_limit)` as the effective limit, so category-specific sub-limits that exceed the global per-claim limit are honoured (e.g., Dental ₹15K > global ₹5K).
- Exclusion matching uses word-boundary regex; partial substring matches do not trigger exclusions. "Lumbar Disc Herniation" does not match the `hernia` exclusion.

---

## Fraud Detection Agent (`app/agents/fraud_detection.py`)

**Input:** `member_id: str`, `claims_history: list[ClaimHistoryItem]`, `claimed_amount: float`, `treatment_date: date`  
**Output:** `FraudResult(signals: list[FraudSignal], should_manual_review: bool)`  
**Errors raised:** None — fraud detection is advisory; errors are swallowed and logged.

**Signal definitions:**

| Signal flag | Trigger |
|-------------|---------|
| `HIGH_FREQUENCY_SAME_DAY` | ≥ 3 claims on the same date as `treatment_date` |
| `HIGH_FREQUENCY_MONTHLY` | > 6 claims in the same calendar month as `treatment_date` |
| `HIGH_VALUE_CLAIM` | `claimed_amount > fraud_thresholds.high_value_threshold` (₹25,000) |

**Invariants:**
- `should_manual_review = True` if any signal is present.
- Fraud signals are informational; the agent does not reject the claim. The Adjudication Agent promotes the decision to `MANUAL_REVIEW` based on `should_manual_review`.
- An empty `claims_history` list always produces `signals=[]`.
- The agent reads `fraud_thresholds` from `PolicyLoader`; thresholds are never hardcoded.

---

## PolicyLoader (`app/services/policy_loader.py`)

**Input:** (none — reads `policy_terms.json` at first call)  
**Output:** `PolicyTerms` Pydantic model  
**Errors raised:** `FileNotFoundError` if `policy_terms.json` is missing; `ValidationError` if the JSON is malformed.

**Invariants:**
- Results are `lru_cache`d for the process lifetime. The file is read exactly once per worker process.
- `get_condition_waiting_period(diagnosis: str) → int | None` returns the waiting period in days for the best-matching condition, or `None` if no condition matches. Matching uses word-boundary regex with an aliases table to avoid false positives.
- `get_document_requirements(category: ClaimCategory) → DocumentRequirements` returns required and optional document types. Returns empty requirements (no required docs) if the category is not listed.

---

## TraceLogger (`app/services/trace_logger.py`)

**Input:** `claim_id: str` (at construction); per-step: `agent, check_name, status, details, confidence_impact`  
**Output:** `ClaimTrace` (via `.build()`)  
**Errors raised:** None.

**Invariants:**
- Steps are stored in insertion order and timestamps are UTC ISO-8601.
- `confidence_impact` must be ≤ 0 (debits only). Passing a positive value is silently treated as 0.
- `overall_confidence = max(0.30, 1.0 + sum(step.confidence_impact for step in steps))`.
- Calling `.build()` is idempotent; it does not clear the step list.
- The logger is not thread-safe. One instance per claim, created fresh by the Orchestrator.

---

## LLM Client (`app/services/llm_client.py`)

**Public functions:**
- `extract_document_data(image_bytes?, image_path?, document_type, extraction_prompt?) → dict`
- `assess_document_quality(image_bytes?, image_path?) → dict`

**Errors raised:**
- `LLMProviderError` — the upstream Gemini API failed after `MAX_ATTEMPTS` (3) retries (network error, rate limit, etc.).
- `LLMSchemaError` — the model returned a response that could not be parsed as JSON or failed `ExtractionLLMResponse` / `QualityLLMResponse` Pydantic validation after all retries.

**Invariants:**
- Both functions are `async`. They must be called from an async context.
- Retries use exponential backoff: 1s, 2s, 4s. Total max wait before raising: ~7s.
- `temperature=0` is always set; generation is deterministic for the same input.
- If both `image_bytes` and `image_path` are `None`, the LLM receives only the text prompt (no image). This is allowed for text-only documents.
- The returned `dict` always matches the shape of `ExtractionLLMResponse.model_dump()` or `QualityLLMResponse.model_dump()` respectively. Callers may rely on all fields being present (with `None` or default values for optional ones).
- The client (`genai.Client`) is a module-level singleton; it is created once per process on first call.
