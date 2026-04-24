# Plum Claims Processor

Multi-agent health insurance claims processing system built for the Plum AI Engineer assignment.

- **Backend:** Python 3.11 + FastAPI + Pydantic + SQLAlchemy (SQLite)
- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS
- **LLM:** Google Gemini 2.0 Flash (vision, only used when a real document file is uploaded)

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full design.

## Results

- **Unit tests:** 18/18 passing (`pytest backend/tests/`)
- **End-to-end eval:** 12/12 test cases passing (`python eval/run_eval.py`) — report at `eval/EVAL_REPORT.md`

## Setup

### Backend

```bash
cd backend
pip install -e .
```

Optional — only needed for real document uploads (test cases use inline content and don't need this):

```bash
export GEMINI_API_KEY=<your key>
```

Run the API:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:5173`. Vite proxies `/api/*` to the backend on port 8000.

## Running tests

Unit tests:

```bash
cd backend
pytest
```

End-to-end against all 12 test cases in `test_cases.json`:

```bash
python eval/run_eval.py
```

This generates `eval/EVAL_REPORT.md` with pass/fail details, decision values, and confidence scores per case.

## Project-layout

```
plum/
├── ARCHITECTURE.md              design doc (read this next)
├── policy_terms.json            all policy rules — read at runtime, never hardcoded
├── test_cases.json              12 test scenarios
├── backend/
│   ├── app/
│   │   ├── agents/              orchestrator, document_gate, extraction, adjudication, fraud_detection
│   │   ├── services/            policy_loader, trace_logger, llm_client
│   │   ├── models/              Pydantic schemas + SQLAlchemy models
│   │   ├── api/                 FastAPI routes
│   │   └── main.py
│   └── tests/                   pytest — one file per agent
├── frontend/
│   └── src/
│       ├── pages/               Dashboard, SubmitClaim, ClaimDetail
│       └── components/          ClaimForm, TraceTimeline, AmountBreakdown, DocumentErrorList, DecisionBadge
└── eval/
    ├── run_eval.py              end-to-end harness
    └── EVAL_REPORT.md           generated report
```

## Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/claims/submit` | Full pipeline, synchronous, returns `ClaimDecision` |
| GET | `/api/claims` | Dashboard list |
| GET | `/api/claims/{id}` | Single claim with trace |
| GET | `/api/policy` | Raw policy terms |
| POST | `/api/test/run-all` | Runs all 12 test cases live |
