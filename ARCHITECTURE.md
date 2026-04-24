# Architecture

A multi-agent health insurance claims processor. Claims enter through a single synchronous API, flow through a fixed pipeline of specialist agents, and return an explainable decision with a full trace.

## Why multi-agent

Each concern in claim processing (document integrity, data extraction, rule adjudication, fraud) has its own inputs, failure modes, and confidence model. Splitting them into independent agents keeps each one focused and testable, makes the pipeline easy to reason about, and localizes the blast radius when a single stage fails. The orchestrator owns ordering and failure recovery so individual agents stay narrow.

## Pipeline

```
ClaimSubmission
      │
      ▼
┌─────────────────┐
│  Orchestrator   │  owns ordering, failure capture, confidence roll-up
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Document Gate  │  type / quality / name checks — STOPS on failure
└────────┬────────┘
         │ (only if gate passed)
         ▼
┌─────────────────┐
│   Extraction    │  dual-path: test-case content OR LLM vision
└────────┬────────┘
         │
         ▼
┌─────────────────┐   ┌──────────────────┐
│  Adjudication   │◀─▶│  Fraud Detection │
└────────┬────────┘   └──────────────────┘
         │
         ▼
   ClaimDecision  (+ ClaimTrace)
```

Every step writes a `TraceStep` via `TraceLogger`. The final `ClaimDecision.trace` contains the full audit trail and `overall_confidence`.

## Agents

### Orchestrator (`app/agents/orchestrator.py`)
- **In:** `ClaimSubmission`
- **Out:** `ClaimDecision`
- Wraps each stage in `try/except`. On failure: appends an `ERROR` trace step, debits confidence by 0.20, and continues with a fallback so the pipeline still produces a decision.
- Handles `simulate_component_failure=True` (TC011) by forcing an extraction failure and routing through the fallback extractor.
- Document Gate failure is the only hard stop — it returns early with `decision=None` and a populated `document_errors` list so the UI can ask for re-upload.

### Document Gate (`app/agents/document_gate.py`)
Three checks, each producing a specific `DocumentError`:
1. **Type completeness** — compares uploaded `actual_type` counts against `policy_terms.document_requirements[category].required`. Error names the missing type by string.
2. **Quality** — flags any doc whose `quality == "UNREADABLE"`. Suggests re-upload rather than rejecting.
3. **Name consistency** — cross-checks `patient_name_on_doc` across docs; flags if more than one distinct name appears.

### Extraction (`app/agents/extraction.py`)
Dual-path by design:
- If `DocumentInput.content` is supplied (all 12 test cases), it's mapped directly into `ExtractedDocument` — no LLM call, deterministic results.
- Otherwise, dispatches to `LLMClient.extract_document_data` (Gemini vision) with a document-type-specific prompt.

Each extracted field carries its own confidence; low-confidence fields debit the trace.

### Adjudication (`app/agents/adjudication.py`)
Rule checks run in this order — ordering matters for test-case expectations:
1. **Exclusions** (diagnosis + line-item text) → `EXCLUDED_CONDITION` (TC012)
2. **Waiting period** (join_date vs treatment_date, word-boundary aliased match) → `WAITING_PERIOD` (TC005)
3. **Pre-authorization** (high-value diagnostic without pre-auth flag) → `PRE_AUTH_MISSING` (TC007)
4. **Per-claim limit** — effective limit = `max(per_claim_limit, category_sub_limit)` → `PER_CLAIM_EXCEEDED` (TC008). Dental sub-limit (₹15K) > per-claim (₹5K), so a ₹12K root canal is not rejected here (TC006).
5. **Annual OPD limit** (`ytd + claim > 50,000`) → reject or cap
6. **Fraud delegation** — see next agent
7. **Amount calculation** for APPROVED/PARTIAL:
   - drop excluded line items (TC006 filters out teeth-whitening)
   - apply network discount if network hospital (**before** copay — TC010: 4500 × 0.80 = 3600)
   - apply copay (TC010: 3600 × 0.90 = 3240; TC004: 1500 × 0.90 = 1350)
   - cap at per-claim limit and remaining annual OPD

### Fraud Detection (`app/agents/fraud_detection.py`)
Pure signal generator. Checks same-day claims count, monthly claim count, and high-value threshold from `fraud_thresholds`. Returns `FraudResult(signals, should_manual_review)`. Adjudication promotes the decision to `MANUAL_REVIEW` when `should_manual_review` is set.

## Policy loading

All rules live in `policy_terms.json` and are read through `PolicyLoader` (`app/services/policy_loader.py`) — nothing is hardcoded. `get_condition_waiting_period` uses word-boundary regex with an aliases table so "Lumbar Disc Herniation" does **not** match the `hernia` waiting period. Loader is cached via `lru_cache` for the process lifetime.

## Data contracts

All IO is Pydantic (`app/models/schemas.py`). Key shapes:

| Model | Purpose |
|-------|---------|
| `ClaimSubmission` | API input — member, category, amount, documents, claims_history, optional `simulate_component_failure` |
| `DocumentInput` | Per-doc: `file_id`, `actual_type`, `quality`, `patient_name_on_doc`, optional `content` |
| `ExtractedDocument` | Agent output — structured fields + per-field confidences |
| `DocumentGateResult` | `{passed, errors: list[DocumentError]}` — the early-stop contract |
| `TraceStep` | `{agent, check_name, status, details, confidence_impact, timestamp}` |
| `ClaimTrace` | `{steps, overall_confidence}` |
| `LineItemDecision` | Per-line approved/rejected + reason |
| `AmountBreakdown` | Step-by-step calculation receipt |
| `ClaimDecision` | Final output — decision, amounts, reasons, line items, breakdown, document_errors, trace, notes |

## API

| Endpoint | Purpose |
|----------|---------|
| `POST /api/claims/submit` | Runs the full pipeline synchronously; returns `ClaimDecision` |
| `GET /api/claims` | Dashboard listing |
| `GET /api/claims/{id}` | Single claim with full trace |
| `GET /api/policy` | Raw policy terms (for UI hints) |
| `POST /api/test/run-all` | Runs all 12 test cases through the live pipeline |

## Confidence model

Starts at 1.0. Debits:
- Component failure: −0.20
- Unreadable document: −0.15
- Partial extraction: −0.10
- Low-confidence extracted field: −0.05 each
- Floor: 0.30. Below 0.60, the orchestrator adds a manual-review note.

## Failure model

The pipeline is designed to **always return a decision** unless the document gate hard-stops it.
- Stage failures are caught at the orchestrator level.
- On extraction failure, `_fallback_extraction` produces a minimal `ExtractedDocument` from the submission itself so adjudication can still run.
- Every failure is recorded as an `ERROR` trace step and surfaces in `ClaimDecision.notes` so the user sees what degraded.

## Testing

- **Unit:** `pytest backend/tests/` — one file per agent, 18 tests.
- **End-to-end:** `python eval/run_eval.py` — loads `test_cases.json`, drives the orchestrator, asserts decisions/amounts/reasons, writes `eval/EVAL_REPORT.md`. Current: **12/12**.

---

## Rejected Alternatives

### Single monolithic agent instead of a pipeline

The simplest implementation would have been one function that checks everything. This was rejected because it conflates failure modes: a document-quality problem is very different from a policy-rule rejection, and they require different caller responses (re-upload vs. appeal). Splitting into agents gives each stage its own confidence model and error type, and lets the orchestrator decide whether a stage failure is recoverable.

### Async fan-out (parallel agents) instead of sequential pipeline

Adjudication depends on extracted data; extraction depends on documents passing the gate. True parallelism would require extracting and gating simultaneously, which gains nothing because extraction is wasted work if the gate fails. The sequential model is simpler and the bottleneck is the LLM call, not orchestration overhead.

### LangChain / LlamaIndex agent framework

Using a pre-built agent framework would have added abstraction over the LLM calls and tool definitions. This was rejected because the pipeline is a fixed, well-understood DAG — it doesn't need dynamic tool selection or autonomous re-planning. The complexity would add framework lock-in and opaque error handling in exchange for no architectural benefit. The current design uses raw `google-genai` SDK with a thin wrapper, which keeps the retry and validation logic explicit and auditable.

### Database-backed trace instead of in-memory TraceLogger

An alternative was to write each `TraceStep` to the database as it happened, for durability mid-flight. This was rejected for the assignment scope: the pipeline is synchronous and short-lived (<2s), so mid-flight durability adds no value. The trace is written to SQLite atomically at the end of the pipeline in a single transaction.

### Gemini structured-output mode (`response_schema=`) instead of JSON prompting

The Gemini API supports passing a `response_schema` to enforce structured output at the API level. This was evaluated but rejected because the schema enforcement happens server-side, which makes validation errors opaque (the API returns a generic error, not the malformed JSON). The current approach — prompt for JSON, parse locally, validate with Pydantic — gives exact error messages, retries on schema failures, and works identically in tests and production.

---

## Scaling to 10× Load

The current design handles one claim per request synchronously. At 10× load these are the limiting factors and their mitigations:

### LLM call latency (primary bottleneck)
- **Problem:** Gemini vision calls take 1–3s per document. A claim with 3 documents takes 3–9s serially.
- **Mitigation:** Fan out per-document extraction calls with `asyncio.gather` inside the Extraction Agent. No architectural change required — the agent is already async.

### SQLite write contention
- **Problem:** SQLite uses file-level locking. At high concurrency, write latency spikes.
- **Mitigation:** Drop-in replace SQLite with PostgreSQL (SQLAlchemy connection string change only). The ORM models are identical; no application code changes.

### Synchronous API endpoint
- **Problem:** `POST /api/claims/submit` blocks while the pipeline runs. At 10× load, workers are exhausted.
- **Mitigation:** Move to a task-queue model — endpoint enqueues a Celery/ARQ job and returns a `claim_id` immediately. Client polls `GET /api/claims/{id}` or uses a WebSocket for push notification. The Orchestrator is already `async` and stateless; it drops into a worker with no changes.

### Policy JSON reload
- **Problem:** `lru_cache` is process-scoped. Multi-worker deploys (Gunicorn, uvicorn workers) each hold their own copy. A policy update requires a rolling restart.
- **Mitigation:** Move `PolicyLoader` to read from a database table with a versioned key. Cache in Redis with a 60s TTL. Policy updates take effect within one TTL without a restart.

### Fraud detection latency
- **Problem:** The current fraud check scans the in-memory `claims_history` passed in the request. At scale, the full history comes from the database.
- **Mitigation:** Add an indexed `(member_id, treatment_date)` query in the Fraud Detection Agent. The existing SQL models support this with one additional query.
