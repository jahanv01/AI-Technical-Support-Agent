"""Task 2: TAM account health summariser."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.config import ACCOUNT_BRIEF_LOOKBACK_DAYS, ACCOUNTS_PATH, TICKETS_PATH
from app.llm_client import generate_structured
from app.pii import redact_text
from app.prompts import account_brief_v1
from app.schemas import AccountBrief, CandidateRisks

_tickets: list[dict] | None = None
_accounts_by_id: dict[str, dict] | None = None
_cutoff: datetime | None = None


def _load() -> tuple[list[dict], dict[str, dict], datetime]:
    global _tickets, _accounts_by_id, _cutoff
    if _tickets is None:
        _tickets = json.loads(TICKETS_PATH.read_text(encoding="utf-8"))
        _accounts_by_id = {a["account_id"]: a for a in json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))}
        max_created = max(datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) for t in _tickets)
        _cutoff = max_created - timedelta(days=ACCOUNT_BRIEF_LOOKBACK_DAYS)
    return _tickets, _accounts_by_id, _cutoff


def _account_tickets(account_id: str, tickets: list[dict], cutoff: datetime) -> list[dict]:
    matches = [
        t for t in tickets
        if t["account_id"] == account_id
        and datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) > cutoff
    ]
    return sorted(matches, key=lambda t: t["ticket_id"])  # deterministic order


def summarize_account(account_id: str) -> AccountBrief:
    tickets, accounts_by_id, cutoff = _load()
    account = accounts_by_id.get(account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")

    recent_tickets = _account_tickets(account_id, tickets, cutoff)
    ticket_ids = [t["ticket_id"] for t in recent_tickets]

    # Redact only for the payload that leaves the process — the quote-
    # grounding checks below compare against the original, unredacted text.
    redacted_notes = [redact_text(n) for n in account["escalation_notes"]]
    redacted_tickets = [
        {**t, "subject": redact_text(t["subject"]), "body": redact_text(t["body"])}
        for t in recent_tickets
    ]
    extract_payload = account_brief_v1.build_extract_payload(redacted_notes, redacted_tickets)
    extract_raw = generate_structured(
        prompt_version=f"{account_brief_v1.VERSION}_extract",
        system_prompt=account_brief_v1.EXTRACT_SYSTEM_PROMPT,
        user_payload={"account_id": account_id, "sorted_ticket_ids": ticket_ids, **extract_payload},
        response_schema=CandidateRisks,
    )
    candidates = CandidateRisks(**extract_raw).candidates

    # Rule-check quote-grounding *before* the synthesize call, rather than
    # trusting the model's own compliance — drop anything ungrounded.
    notes_blob = " ".join(account["escalation_notes"])
    tickets_by_id = {t["ticket_id"]: t for t in recent_tickets}
    verified = [
        c for c in candidates
        if (c.ticket_id == "account_notes" and c.quote in notes_blob)
        or (c.ticket_id in tickets_by_id and c.quote in tickets_by_id[c.ticket_id]["body"])
    ]

    synthesize_payload = account_brief_v1.build_synthesize_payload(
        account={
            "company": account["company"],
            "plan_tier": account["plan_tier"],
            "arr_usd": account["arr_usd"],
            "health_status": account["health_status"],
            "usage_trend": account["usage_trend"],
            "open_tickets": account["open_tickets"],
            "p1_tickets_last_30d": account["p1_tickets_last_30d"],
            "renewal_date": account["renewal_date"],
            "nps_score": account["nps_score"],
            "primary_contact": account["primary_contact"],
            "region": account["region"],
            "industry": account["industry"],
        },
        verified_risks=[v.model_dump() for v in verified],
        ticket_count_last_90d=len(recent_tickets),
    )
    synthesize_raw = generate_structured(
        prompt_version=f"{account_brief_v1.VERSION}_synthesize",
        system_prompt=account_brief_v1.SYNTHESIZE_SYSTEM_PROMPT,
        user_payload={"account_id": account_id, "sorted_ticket_ids": ticket_ids, **synthesize_payload},
        response_schema=AccountBrief,
    )
    brief = AccountBrief(**synthesize_raw)
    brief.account_id = account_id
    brief.generated_from_ticket_ids = ticket_ids
    brief.prompt_version = account_brief_v1.VERSION

    # Same defensive guard as triage.py: never let a risk through whose quote
    # isn't actually grounded, even if the synthesize call altered one.
    brief.risks = [
        r for r in brief.risks
        if (r.ticket_id == "account_notes" and r.quote in notes_blob)
        or (r.ticket_id in tickets_by_id and r.quote in tickets_by_id[r.ticket_id]["body"])
    ]

    return brief
