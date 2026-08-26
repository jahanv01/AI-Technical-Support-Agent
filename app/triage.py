"""Task 1: ticket triage.

TODO(you): implement classify_ticket(). High-level flow:
  1. Build/reuse a KBIndex (app.retrieval) — build once at module load or
     pass in, don't rebuild per call.
  2. Search the KB with the ticket subject+body as the query; keep only the
     top match if its score clears config.KB_MATCH_SCORE_THRESHOLD.
  3. Call llm_client.generate_structured() with prompts.triage_v1, passing
     the ticket text + (possibly empty) KB excerpt.
  4. Validate the response against TriageOutput and return it.

Do NOT pass ticket.category / ticket.urgency (ground-truth labels) into the
prompt — those exist only so eval/cases_triage.json can grade accuracy.
"""
from __future__ import annotations

from app.retrieval import KBIndex
from app.schemas import TicketIn, TriageOutput

_kb_index: KBIndex | None = None


def _get_kb_index() -> KBIndex:
    global _kb_index
    if _kb_index is None:
        _kb_index = KBIndex.build()
    return _kb_index


def classify_ticket(ticket: TicketIn) -> TriageOutput:
    raise NotImplementedError
