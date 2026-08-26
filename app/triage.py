"""Task 1: ticket triage."""
from __future__ import annotations

from app.config import KB_MATCH_SCORE_THRESHOLD
from app.llm_client import generate_structured
from app.pii import redact_text
from app.prompts import triage_v1
from app.retrieval import KBIndex
from app.schemas import TicketIn, TriageOutput

_kb_index: KBIndex | None = None


def _get_kb_index() -> KBIndex:
    global _kb_index
    if _kb_index is None:
        _kb_index = KBIndex.build()
    return _kb_index


def classify_ticket(ticket: TicketIn) -> TriageOutput:
    kb_index = _get_kb_index()
    query = f"{ticket.subject} {ticket.body}"
    candidates = [
        {"heading": chunk.heading, "text": chunk.text}
        for chunk, score in kb_index.search(query, top_k=2)
        if score >= KB_MATCH_SCORE_THRESHOLD
    ]

    # Redact only for the payload that leaves the process — KB retrieval
    # above is local, so it uses the original text.
    user_payload = triage_v1.build_user_payload(
        redact_text(ticket.subject), redact_text(ticket.body), candidates,
    )

    raw = generate_structured(
        prompt_version=triage_v1.VERSION,
        system_prompt=triage_v1.SYSTEM_PROMPT,
        user_payload=user_payload,
        response_schema=TriageOutput,
    )
    output = TriageOutput(**raw)

    # Guard against a hallucinated citation even if the model ignores the
    # prompt instruction: only trust matched_kb_doc if it's actually one of
    # the candidates we offered.
    candidate_headings = {c["heading"] for c in candidates}
    if output.matched_kb_doc and output.matched_kb_doc not in candidate_headings:
        output.matched_kb_doc = None

    return output
