# Demo Script & Project Explanation Guide

Everything you need to record the video and answer the technical review.

---

## The Three Things The Assignment Requires

The marking rubric explicitly asks for these three in the video. Everything else is context.

| # | Requirement | Where in this script |
|---|-------------|----------------------|
| 1 | Claim stopped early due to a document problem — show the error message | Scene 3 |
| 2 | Successful end-to-end approval with full trace visible | Scene 4 |
| 3 | One technical decision you're proud of + one you'd change | Scene 7 |

---

## 30-Second Pitch (memorise this)

> "This is a multi-agent health insurance claims processing system. An employee submits a claim with their documents. The system validates those documents, extracts structured data from them using Gemini Vision AI, applies the company's policy rules, detects fraud, and produces a final decision — APPROVED, PARTIAL, REJECTED, or MANUAL REVIEW — with a full audit trail showing every check that ran. No human in the loop for straightforward claims."

---

## Before Recording — Setup Checklist

- [ ] Backend running: `cd backend && uvicorn app.main:app --reload --port 8000`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] Browser open on Dashboard (`localhost:5173`)
- [ ] `adjudication.py` open in editor, scrolled to the amount calculation section
- [ ] `llm_client.py` open in editor
- [ ] Dashboard is empty (hit Clear All if needed — fresh start looks cleaner)

---

## VIDEO SCRIPT

---

### Scene 1 — Opening (0:00–0:40)

**Show:** Dashboard, empty or with a couple of claims

> "Hi, I'm [name]. This is my submission for the Plum AI Engineer assignment.
>
> What you're looking at is a live multi-agent system that automates health insurance claim processing — running on Railway for the backend and Vercel for the frontend, both deployed from this GitHub repo.
>
> I'm going to show you three things the assignment asked for: a claim stopped early by a document error, a successful end-to-end approval with the full audit trail, and the two technical decisions I want to explain — one I'm proud of, one I'd change.
>
> Let me start."

---

### Scene 2 — Architecture in 60 Seconds (0:40–1:45)

**Show:** `ARCHITECTURE.md` — the pipeline diagram at the top

> "Five agents. One pipeline. The Orchestrator is the only entry point — it calls the others in sequence.
>
> First the Document Gate runs before anything else. If the documents are wrong, we stop immediately. No LLM called, no policy rules touched.
>
> If the gate passes, the Extraction Agent pulls structured fields from the documents — directly from test data, or via Gemini Vision for real uploaded images.
>
> Then Adjudication runs seven policy rules and calculates the approved amount. It calls the Fraud Detection Agent at step six.
>
> Every step writes to a TraceLogger with a confidence score. The final decision embeds the complete audit trail — not in server logs, in the decision object itself."

---

### ★ Scene 3 — REQUIRED: Claim Stopped by Document Error (1:45–3:30)

**This is required item #1. Show the error message clearly on screen.**

**Show:** Browser → click **New Claim**

**Fill in the form:**
- Member ID: `EMP002`
- Category: `CONSULTATION`
- Treatment Date: `2024-11-01`
- Claimed Amount: `800`
- Hospital: leave blank
- Documents: **delete the second row so only 1 document remains** (PRESCRIPTION only)
- Hit **Submit Claim**

> "CONSULTATION requires two documents — a prescription and a hospital bill. I've only uploaded a prescription. Let's see what happens."

**[wait for response — ~1 second]**

**Show:** The claim detail page — no decision badge, document errors section highlighted

> "The pipeline stopped. Notice there's no decision here — no APPROVED, no REJECTED. The Document Gate caught this before extraction ran, before any policy rules ran, before any LLM was called.
>
> The error message says exactly what's missing: 'Missing required document type: HOSPITAL_BILL. Please upload the required document to proceed.'
>
> This is an important design decision. A document problem is recoverable — the member re-uploads and resubmits. A policy rejection is final. The system treats them completely differently. Document errors don't create a claim record that says REJECTED. They're a prompt to fix and try again.
>
> And the error message is specific and actionable — it names the missing type, not just 'document error'."

**[Optional — also click TC003 from the test results grid if you've run tests]**

> "TC003 tests the name mismatch case — two documents with different patient names. Same outcome: pipeline stops, error tells the user exactly which documents conflict and what to re-upload."

---

### ★ Scene 4 — REQUIRED: End-to-End Approval with Full Trace (3:30–6:30)

**This is required item #2. Walk through every trace step visibly on screen.**

**Show:** Dashboard → hit **Run All Test Cases**

> "Let me run all 12 test cases through the live pipeline."

**[wait for 12/12 green grid]**

> "12 out of 12 passing. Let me click TC004 — the clean consultation, full approval."

**Show:** TC004 claim detail page

> "Decision: APPROVED. Approved amount: ₹1,350. Let me walk through exactly how the system got there.
>
> Starting on the right — the trace timeline. This is every check that ran, in order, with the result of each one."

**[scroll through trace steps, pointing at each]**

> "Document Gate — three checks. Type completeness: PRESCRIPTION and HOSPITAL_BILL both present — PASSED. Quality check: both documents readable — PASSED. Name consistency: both show Priya Sharma — PASSED. Gate cleared.
>
> Extraction — two documents, both extracted directly from inline content. No LLM needed for test cases. Confidence still 100%.
>
> Adjudication — now the seven policy rules. Exclusions check: diagnosis is 'Acute Respiratory Infection' — not in the exclusions list — PASSED. Waiting period: no waiting period for this condition — PASSED. Pre-authorization: consultation, not a high-value diagnostic — PASSED. Per-claim limit: ₹1,500 is under the ₹5,000 cap — PASSED. Annual OPD: ₹0 year-to-date — PASSED. Fraud check: first claim, no signals — PASSED.
>
> Then the amount calculation. Claimed ₹1,500. No exclusions removed. Not a network hospital — no network discount. Copay is 10% — ₹1,500 × 0.90 = ₹1,350.
>
> Confidence: 100%. Every check passed, nothing debited."

**[scroll to amount breakdown on the left]**

> "The amount breakdown on the left shows that step-by-step calculation. Original → no exclusions → no network discount → after 10% copay = ₹1,350.
>
> An auditor or an ops person can open any claim and reconstruct every decision from this page. Nothing is a black box. The trace is stored inside the decision object — not in server logs that get rotated, in the claim record itself."

---

### Scene 5 — Code Walkthrough (6:30–8:00)

**Show:** `adjudication.py` — the amount calculation section

> "Let me show two pieces of code that matter.
>
> First — the adjudication rule order. Exclusions run before the per-claim limit check. This is load-bearing. TC006 is a dental claim for ₹12,000 — root canal plus teeth whitening. Whitening is excluded. If we checked the ₹5,000 per-claim limit first, this would be REJECTED — ₹12,000 exceeds the global limit. But the correct behavior is: remove the excluded whitening item first, leaving ₹8,000 of covered dental work. Dental sub-limit is ₹15,000 — ₹8,000 passes. Result is PARTIAL ₹8,000. The order of these seven rules is documented in ARCHITECTURE.md and tested by TC006."

**Show:** `llm_client.py`

> "Second — the LLM integration. Three hardening decisions.
>
> Pydantic schema validation — the model must return JSON that matches `ExtractionLLMResponse`. If it doesn't, we get `LLMSchemaError`, not a random KeyError deep inside adjudication.
>
> Retry with exponential backoff — three attempts at 1s, 2s, 4s. Schema errors are retryable because the model sometimes self-corrects on the second try with the same prompt.
>
> Temperature zero — deterministic output. The same document always produces the same extraction. You can't have an auditable claims system if the same input gives different decisions on different runs."

---

### Scene 6 — Graceful Failure (8:00–8:45)

**Show:** Click **TC011** from the test grid

> "TC011 deliberately crashes the extraction component — I pass `simulate_component_failure: true`.
>
> The orchestrator catches the exception, logs an ERROR trace step — you can see it here in red — debits confidence by 0.20, and continues with a fallback that rebuilds a minimal document from the submission fields alone.
>
> Adjudication still runs. Decision: APPROVED ₹4,000. Confidence: 80%.
>
> The pipeline never crashed. The note says 'Extraction component failed. Processing continued with limited data. Manual review recommended.' The system degraded gracefully and told the user exactly what happened."

---

### ★ Scene 7 — REQUIRED: Proud Of + Would Change (8:45–10:00)

**This is required item #3. Say both parts clearly.**

**Show:** `adjudication.py` — the amount calculation, specifically the network discount line

> "The technical decision I'm most proud of is the amount calculation order — network discount is applied before copay, not after. TC010: ₹4,500 at a network hospital. 20% network discount first: ₹4,500 × 0.80 = ₹3,600. Then 10% copay: ₹3,600 × 0.90 = ₹3,240.
>
> It's a small thing. In this specific case the arithmetic gives the same answer either way. But with cumulative sub-limits and partial exclusions, the order changes the number — and the policy document specifies this order explicitly. I read it, coded it correctly, and documented the invariant in ARCHITECTURE.md specifically so a future maintainer can't accidentally reverse it during a refactor. Getting that right, and making sure it can't silently break, is what I'm proud of."

**[pause — move to a different part of the screen or look at camera]**

> "The thing I'd change is the database. SQLite is fine for this scope — zero config, easy to run locally. But on Railway, the filesystem is ephemeral. Every container restart wipes the claims history. That's why there's a 'Run All Test Cases' button — to repopulate data after a redeploy.
>
> In production I'd swap SQLite for PostgreSQL. Railway has a managed Postgres addon. Because I'm using SQLAlchemy, it's literally a one-line change in `config.py` — swap the connection string. I documented this in LIMITATIONS.md and it's the first item on the future work list."

---

### Scene 8 — Close (10:00–10:30)

**Show:** Dashboard with 12/12 green tiles

> "To summarise: five-agent pipeline, 12 out of 12 test cases passing, 18 unit tests, full audit trail on every decision, graceful failure handling, Gemini Vision for real document extraction, and a policy rule engine that reads from JSON — nothing hardcoded.
>
> The system is live. Backend on Railway, frontend on Vercel. Link is in the submission.
>
> Thank you."

---

## Technical Review — Q&A

### Architecture

**"Walk me through a claim submission."**
> POST hits FastAPI. Pydantic validates the body. Orchestrator spins up, creates a TraceLogger at confidence 1.0. Calls Document Gate — three checks, stops if any fail. Calls Extraction — maps content or calls Gemini Vision. Calls Adjudication — seven rules, delegates fraud check, calculates amount. Builds ClaimDecision with the full trace. Persists to SQLite. Returns ClaimDecision. Frontend redirects to the detail page.

**"Why is the pipeline sequential and not parallel?"**
> Adjudication needs extraction output. Extraction needs the gate to pass. Each stage's input is the previous stage's output — there's no independent work to run in parallel at the pipeline level. Within extraction, per-document calls could be parallelized with `asyncio.gather` — that's the first scaling change I'd make.

**"Why not use LangChain or an agent framework?"**
> The pipeline is a fixed DAG, not a dynamic replanning loop. LangChain is designed for autonomous tool selection and multi-step reasoning — neither is needed here. Adding it would introduce framework lock-in and make the retry and validation logic opaque. Raw `google-genai` with a thin wrapper keeps everything explicit and auditable.

**"Why Gemini and not GPT-4?"**
> Free tier with generous limits, strong vision performance on Indian medical documents, and a Python SDK that supports structured JSON prompting cleanly. It's configurable — swapping the model is a one-line env var change (`GEMINI_MODEL` in Railway settings). No code change needed.

**"What happens if the database goes down?"**
> The pipeline runs entirely in memory. SQLite is only written at the very end. If the write fails, the pipeline result is lost but the system doesn't crash. In production, you'd use a task queue with retry-on-write.

---

### Rule Engine

**"Why does rule ordering matter?"**
> Dental example: TC006, ₹12,000 root canal + teeth whitening. Whitening is excluded. If per-claim limit ran before exclusions, ₹12,000 exceeds the ₹5,000 global cap → REJECTED. Correct behavior: remove excluded whitening first → ₹8,000 covered work → dental sub-limit is ₹15,000 → PASSED → PARTIAL ₹8,000. Exclusions must run before per-claim.

**"How does the waiting period check work?"**
> `PolicyLoader.get_condition_waiting_period(diagnosis)` runs word-boundary regex with an aliases table against the diagnosis string. Returns the period in days or None. Adjudication checks `(treatment_date - member_join_date).days < period`. Word-boundary prevents false matches — "Lumbar Disc Herniation" doesn't match the hernia waiting period.

**"How does partial approval work?"**
> Only DENTAL has line-item-level exclusion checking. When some items are excluded and some are covered, result is PARTIAL. Each line item gets a `LineItemDecision` — APPROVED or REJECTED with a reason. The sum of approved items becomes the working amount, then goes through discount/copay/cap.

**"What if the claimed amount doesn't match the sum of line items?"**
> The system trusts `claimed_amount` as authoritative. Line items are used only to identify excluded items. Final approved amount is `claimed_amount` minus excluded item amounts. Discrepancies show in the amount breakdown.

---

### Failure Handling

**"What if Gemini is down?"**
> Three retries with backoff. After all three fail, `LLMProviderError` is raised. Orchestrator catches it, logs ERROR trace step, debits confidence 0.20, calls `_fallback_extraction` which rebuilds a minimal document from the ClaimSubmission fields. Adjudication still runs. Confidence ≤ 0.80, note says extraction failed.

**"What if you get malformed JSON from the LLM?"**
> `_parse_and_validate` raises `LLMSchemaError`. `_with_retry` catches it and retries — the model often self-corrects on the second try. If all three attempts fail, `LLMSchemaError` is re-raised and the orchestrator handles it the same as a provider error.

**"How do you test without a real Gemini API key?"**
> All 12 test cases use the `content` field on `DocumentInput` — extraction maps it directly, no LLM call. The test suite and eval harness run fully offline. Without a key, the orchestrator catches `LLMProviderError` from real file uploads, logs an ERROR step, debits confidence, and continues with fallback extraction.

---

### Extension Questions (live coding)

**"Add a rule: claims from unregistered providers go to manual review."**
> 1. Add `provider_verification` section to `policy_terms.json`
> 2. Add `is_registered_provider(name)` accessor to `PolicyLoader`
> 3. In `AdjudicationAgent.process`, after fraud check (step 6), extract `doctor_name` from extracted docs, call the accessor, if unregistered → trace step + `MANUAL_REVIEW`
> 4. One unit test in `test_adjudication.py`

**"Add a daily claim limit per member."**
> 1. In `AdjudicationAgent` or a pre-gate check in Orchestrator
> 2. Query `SELECT COUNT(*) FROM claim_records WHERE member_id = ? AND treatment_date = ?`
> 3. If ≥ 3, return `DocumentError(error_type="DAILY_LIMIT_EXCEEDED", message="...")`
> 4. No schema changes needed

**"Support PDF uploads."**
> PDFs are already accepted by the upload endpoint — `accept="image/*,application/pdf"` in the file picker, endpoint saves the bytes. The only remaining change: in `llm_client.py`, detect MIME type from the file suffix and pass `mime_type="application/pdf"` to `types.Part.from_bytes`. Gemini 2.5 Flash handles PDFs natively. One conditional, nothing else changes.

**"Make it handle 10 claims at the same time."**
> Orchestrator and all agents are already `async`. Two blockers: (1) synchronous HTTP response — move to a task queue (ARQ/Celery), endpoint returns `{claim_id, status: pending}`, client polls; (2) SQLite single-writer — swap for PostgreSQL, one-line connection string change. No agent code changes needed.

---

## The Two Required Answers (memorise these)

### Decision I'm Proud Of

> "The amount calculation order — network discount before copay. TC010: ₹4,500 × 0.80 × 0.90 = ₹3,240. The policy document specifies this order and I coded it correctly. But more importantly, I documented the invariant in ARCHITECTURE.md so a future maintainer knows it's load-bearing and can't silently reverse it during a refactor. It's a small thing done correctly and made durable."

### Thing I'd Change

> "The database. SQLite is zero config and works perfectly for this scope, but it's ephemeral on Railway — every container restart wipes claims history. In production I'd use PostgreSQL. Railway has a managed Postgres addon. Because I'm using SQLAlchemy, it's a one-line connection string change in `config.py`. I documented this in LIMITATIONS.md as the first priority."

---

## Things NOT to Say

- "I didn't have time to..." → "This is in LIMITATIONS.md as future work because..."
- "The LLM makes the policy decisions" → it does NOT. LLM extracts data. Decisions are deterministic Python reading `policy_terms.json`.
- "The tests are mocked" → they are not. Eval harness runs the real orchestrator with real policy rules.
- "I'm not sure how that works" → "Let me show you in the code" — you have it open.
