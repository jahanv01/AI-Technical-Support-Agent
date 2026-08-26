# AI Technical Support Agent

Zycus AI Engineer Intern take-home: an LLM-powered ticket triage agent (Task 1),
a TAM account health summariser (Task 2), and an eval harness for both (Task 3).
Design note: [DESIGN_NOTE.md](DESIGN_NOTE.md). Prompt version history: [PROMPT_CHANGELOG.md](PROMPT_CHANGELOG.md).

## Quick start (Linux / macOS / WSL)

```bash
git clone <this-repo-url>
cd AI-Technical-Support-Agent
./install.sh --api-key YOUR_GEMINI_KEY
```

That's it. The script creates a venv, installs dependencies, writes `.env`,
and starts the API server in the background. Follow the printed URLs to try
the endpoints. Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

```bash
./uninstall.sh          # stop server + remove .venv and .cache
./uninstall.sh --keep-env  # stop server only, keep .venv
```

> **Windows (native):** use the manual steps below instead.

---

## Setup from scratch

### 1. Clone the repository

```bash
git clone <this-repo-url>
cd AI-Technical-Support-Agent
```

### 2. Dataset

Unlike a typical assignment repo, the mock dataset is **already included** —
`data/tickets.json` (500 tickets), `data/accounts.json` (50 accounts), and
`knowledge-base/*.md` (9 docs) are committed as-is, since they're required
for the eval harness and CI to run without any manual setup step. See
[data/README.md](data/README.md) for field-level documentation.

### 3. Create a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Then open `.env` and set `GEMINI_API_KEY` (free tier key from
[aistudio.google.com/apikey](https://aistudio.google.com/apikey)). The
default model (`GEMINI_MODEL` / `GEMINI_JUDGE_MODEL`) is already set to a
working free-tier model — see the note in `.env.example` if you need to
change it.

## Sample run — Task 1 (triage)

```bash
uvicorn app.api:app --reload
```

Interactive docs (Swagger UI): http://127.0.0.1:8000/docs

```bash
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

> Requires the server from Task 1 to be running (`uvicorn app.api:app --reload`).

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
