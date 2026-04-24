# Known Limitations and Future Work

This document is an honest accounting of what the current system does not do and why. It is intended for reviewers, not users — the system is correct within its defined scope.

---

## Scope Limitations (by design)

### Only OPD claims
The policy model (`policy_terms.json`) covers outpatient (OPD) claims. Inpatient (IPD) hospitalisation claims have different rule sets — room rent sub-limits, surgery tables, pre/post hospitalisation windows — and are not implemented. The `ClaimCategory` enum includes only OPD categories.

### Single-policy system
Every claim is evaluated against `PLUM_GHI_2024`. In production, a member may have multiple active policies (individual + group), and adjudication must sequence them correctly (primary vs. secondary coverage). This is not implemented.

### Member database is not real
Member join date, policy inception date, and pre-existing conditions are read from `policy_terms.json` defaults, not from a real member database. All members are assumed to have joined on the policy's effective date unless overridden in the test case.

### No real file upload pipeline
The `POST /api/claims/upload` endpoint stores files on local disk. There is no S3/GCS bucket, no virus scan, no file-type validation beyond MIME header inspection. In production, uploaded files must be isolated from the application process and scanned before extraction.

---

## AI / LLM Limitations

### Vision extraction accuracy is untested at scale
The extraction agent's dual-path design means all 12 eval cases use `content`-path (no LLM call). The Gemini vision path is implemented and works on manual tests, but its accuracy on real Indian medical documents (mixed languages, handwritten prescriptions, low-resolution scans) is not benchmarked. Expect a meaningful false-negative rate on blurry or handwritten documents.

### Prompt is English-only
The extraction prompt is English. Many Indian prescriptions include Hindi or regional-language text. Gemini 2.0 Flash handles multilingual input reasonably, but the structured-output prompt has not been tuned for non-Latin scripts.

### Retry on schema error is a workaround
The `_with_retry` function retries on `LLMSchemaError` (malformed JSON from the model). This works in practice but is a workaround for non-deterministic model output. The correct fix is to use the Gemini `response_schema` parameter for server-side structure enforcement — this was deferred due to the opacity of server-side validation errors (see `ARCHITECTURE.md` for details).

### No human-in-the-loop for MANUAL_REVIEW decisions
`MANUAL_REVIEW` decisions are surfaced in the UI but there is no workflow for a human adjudicator to review and approve/reject them. The decision sits in the database indefinitely.

---

## Rule Engine Limitations

### Waiting periods use policy default join date
The waiting period check computes `treatment_date - member_join_date`. Because there is no real member database, `member_join_date` defaults to the policy effective date (`2024-01-01`). Any claim submitted before `2024-01-01` + waiting_period_days would be incorrectly flagged.

### No pre-existing condition tracking
The exclusions list covers conditions that are always excluded (cosmetic, obesity, etc.). It does not model pre-existing conditions declared at enrolment — those require per-member data not available in the current design.

### Fraud detection uses only the claim history passed in the request
The fraud agent does not query the database for a member's full history. It operates only on the `claims_history` array provided in the `ClaimSubmission`. A caller who omits `claims_history` will never trigger fraud signals. In production, this must be fetched server-side.

### No appeals or resubmission workflow
Once a claim is `REJECTED`, there is no mechanism to appeal or resubmit with corrected documents. The API allows re-submitting (a new claim_id is generated), but the system has no concept of claim lineage or prior adjudication history for the same episode.

---

## Infrastructure Limitations

### SQLite is single-writer
SQLite serialises writes. At more than ~5 concurrent requests, write latency will degrade. The ORM is PostgreSQL-compatible; switching is a one-line connection string change.

### No authentication or authorisation
The API has no auth layer. Any caller can submit claims for any `member_id` and read any claim. In production, endpoints must be gated behind an identity provider with member-scoped access control.

### Secrets are environment variables
`GEMINI_API_KEY` is read from the environment. There is no secrets rotation, audit logging, or secret store integration (e.g., Vault, AWS Secrets Manager).

### No observability beyond trace
The system writes structured `TraceStep` logs per claim but has no metrics export (Prometheus, Datadog), no distributed tracing (OpenTelemetry), and no alerting. In production, LLM call latency, failure rates, and confidence score distributions should be instrumented.

---

## Future Work (priority order)

1. **Real member database** — store member join dates, pre-existing conditions, and active policies per member.
2. **Async + task queue** — move `POST /api/claims/submit` to enqueue a background job; return `claim_id` immediately; add a status endpoint.
3. **PostgreSQL migration** — swap SQLite for PostgreSQL; add Alembic migration scripts.
4. **Auth layer** — add JWT/OAuth2 with member-scoped access.
5. **Human-in-the-loop workflow** — add a `/api/claims/{id}/adjudicate` endpoint for manual review queue.
6. **Gemini structured-output mode** — switch to `response_schema=` for server-enforced structure, replacing the parse-and-retry workaround.
7. **Multilingual extraction prompt** — tune the extraction prompt for Hindi and regional Indian languages.
8. **IPD claims** — extend `policy_terms.json` and adjudication rules to cover inpatient hospitalisation.
9. **File storage** — replace local disk storage with S3-compatible object store + antivirus scan on upload.
10. **Observability** — add OpenTelemetry spans around each agent stage and Prometheus metrics for confidence distribution and LLM error rates.
