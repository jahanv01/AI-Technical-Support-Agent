# AI Technical Support Agent

Zycus AI Engineer Intern take-home: an LLM-powered ticket triage agent (Task 1),
a TAM account health summariser (Task 2), and an eval harness for both (Task 3).
Design note: [DESIGN_NOTE.md](DESIGN_NOTE.md). Prompt version history: [PROMPT_CHANGELOG.md](PROMPT_CHANGELOG.md).

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in GEMINI_API_KEY
```

Mock dataset (`data/tickets.json`, `data/accounts.json`, `knowledge-base/*.md`)
is already included in this repo — see [DATA_SCHEMA.md](DATA_SCHEMA.md) for
field documentation.

## Sample run — Task 1 (triage)

```bash
uvicorn app.api:app --reload
curl -X POST http://127.0.0.1:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "SSO configuration not working for new users", "body": "308 people blocked from accessing the platform..."}'
```

Or as a plain function:

```python
from app.triage import classify_ticket
from app.schemas import TicketIn

result = classify_ticket(TicketIn(subject="...", body="..."))
print(result.model_dump_json(indent=2))
```

## Sample run — Task 2 (account brief)

```bash
curl http://127.0.0.1:8000/account-brief/ACC-2944
```

```python
from app.account_brief import summarize_account

brief = summarize_account("ACC-2944")
print(brief.model_dump_json(indent=2))
```

## Eval harness (Task 3)

```bash
python -m eval.run_eval
```

Writes `eval_report.json` and `eval_report.md` to the repo root. Exits
non-zero if any case fails below the quality threshold (see
`eval/run_eval.py`), so it can gate CI. 6 test cases per task, one adversarial
each — see `eval/cases_triage.json` / `eval/cases_account.json`.

**Note on ground truth**: the dataset's `category`/`urgency` fields are
decorrelated from actual ticket content (verified across all 500 tickets —
see [data/README.md](data/README.md)), so eval acceptance criteria are
content-grounded (what the ticket text actually says), not graded against
those fields.

## Bonus demo UI (Streamlit)

```bash
streamlit run ui/streamlit_app.py
```

## Project layout

```
app/            triage + account-brief pipelines, schemas, Gemini client, retrieval, FastAPI
eval/           test cases, rule-based + LLM-judge scoring, report generator
ui/             Streamlit demo
data/           mock dataset (tickets, accounts)
knowledge-base/ product docs (RAG corpus)
```
