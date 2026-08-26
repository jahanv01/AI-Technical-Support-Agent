"""Task 2: TAM account health summariser.

TODO(you): implement summarize_account(). High-level flow:
  1. Load accounts.json / tickets.json (see DATA_SCHEMA.md's
     get_account_tickets() for the join+90-day-filter pattern — but derive
     the cutoff from the max created_at in the dataset, not datetime.now(),
     so results are stable across runs/days).
  2. Sort the filtered tickets deterministically (e.g. by ticket_id) before
     building any prompt payload.
  3. Call 1: llm_client.generate_structured() with
     prompts.account_brief_v1.EXTRACT_SYSTEM_PROMPT to get candidate risk
     signals from tickets + account.escalation_notes.
  4. Rule-check: drop/flag any candidate whose `quote` is not an exact
     substring of its source ticket body / escalation note (see
     eval/rules.py — reuse the same check here, not just at eval time).
  5. Call 2: SYNTHESIZE_SYSTEM_PROMPT with the account summary + verified
     candidates to produce the final 3-section AccountBrief.
  6. Both calls go through llm_client's cache, keyed on
     (account_id, sorted ticket_ids, prompt_version) — this is what
     guarantees determinism, not temperature alone.

Handle the case where account_id has no matching account record (dataset
has intentional gaps, per DATA_SCHEMA.md) — return a clear "not found"
result rather than raising.
"""
from __future__ import annotations

from app.schemas import AccountBrief


def summarize_account(account_id: str) -> AccountBrief:
    raise NotImplementedError
