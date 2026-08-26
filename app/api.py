"""FastAPI entry point.

Run with: uvicorn app.api:app --reload
"""
from fastapi import FastAPI, HTTPException

from app.account_brief import summarize_account
from app.schemas import AccountBrief, TicketIn, TriageOutput
from app.triage import classify_ticket

app = FastAPI(title="AI Technical Support Agent")


@app.post("/triage", response_model=TriageOutput)
def triage_endpoint(ticket: TicketIn) -> TriageOutput:
    try:
        return classify_ticket(ticket)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="classify_ticket not implemented yet")


@app.get("/account-brief/{account_id}", response_model=AccountBrief)
def account_brief_endpoint(account_id: str) -> AccountBrief:
    try:
        return summarize_account(account_id)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="summarize_account not implemented yet")
