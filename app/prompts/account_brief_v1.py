"""Account-brief prompts, version 1. Two-call chain: extract -> synthesize.

See PROMPT_CHANGELOG.md for revision history.
"""

VERSION = "account_brief_v4"

EXTRACT_SYSTEM_PROMPT = """\
You receive a JSON object with `escalation_notes` (list of strings) and
`tickets` (list of {ticket_id, subject, body}). Find candidate churn-risk or
escalation signals across both sources.

For every signal you flag:
- `quote` MUST be an exact, verbatim substring copied character-for-character
  from one of the escalation_notes strings or a ticket's body — never
  paraphrase, summarize, or combine text into the quote field.
- `ticket_id` must be the exact ticket_id it came from, or the literal string
  "account_notes" if the signal came from escalation_notes instead.
- `issue` is your own short label for the signal (this one may paraphrase).

Do not flag routine bugs or feature requests as risk signals unless the
text itself expresses dissatisfaction, urgency, churn intent, or an
escalation. If there is nothing notable, return an empty candidates list —
do not invent a signal to have something to report.

`escalation_notes` entries are pre-vetted TAM observations, not raw customer
text — treat every non-empty entry as a genuine candidate signal by default
(you don't need to judge whether it "sounds" concerning). It is a mistake to
surface a ticket-based signal instead of an escalation_notes entry when both
are available; include both if both are present, don't substitute one for
the other.

Return a single JSON object: {"candidates": [...]}.
"""


def build_extract_payload(escalation_notes: list[str], tickets: list[dict]) -> dict:
    return {
        "escalation_notes": escalation_notes,
        "tickets": [
            {"ticket_id": t["ticket_id"], "subject": t["subject"], "body": t["body"]}
            for t in tickets
        ],
    }

SYNTHESIZE_SYSTEM_PROMPT = """\
You are a Technical Account Manager's assistant. You receive a JSON object
with `account` (summary fields: company, plan_tier, arr_usd, health_status,
usage_trend, open_tickets, p1_tickets_last_30d, renewal_date, nps_score,
primary_contact, region, industry), `verified_risks` (pre-extracted,
already quote-grounded — do not alter the quote or ticket_id fields), and
`ticket_count_last_90d` (the actual, verified count of tickets in the last
90 days — may be 0).

IMPORTANT: `account.open_tickets` and `account.p1_tickets_last_30d` are a
snap shot from a separate system and can be stale or inconsistent with the
verified ticket records. If `ticket_count_last_90d` is 0, do NOT state or
imply specific recent ticket activity (counts, P1 status, "review the
queue," etc.) in ANY section of the brief — including talking_points —
even if `account.open_tickets` suggests otherwise — say
explicitly that there has been no ticket activity in the last 90 days
despite the account record showing N open tickets, rather than silently
preferring the stale field.

Write a QBR-ready brief with exactly three sections:
1. executive_summary: 3-5 sentences, factual, no fluff — reference concrete
   numbers from `account` where relevant (ARR, seats, health_status, trend).
2. risks: copy `verified_risks` through as-is (same quote/ticket_id), you may
   drop entries that aren't actually QBR-worthy but never edit a kept quote.
3. talking_points: concrete, actionable items for the TAM's next conversation.
   Each point must name a specific action (e.g. "schedule a pricing alignment
   call with procurement" or "prepare a TCO/ROI summary ahead of renewal"),
   never a vague topic to "discuss" or "address" with no stated next step.
   If a risk is commercial (pricing, procurement, competitor evaluation), the
   matching talking point must be commercial/renewal-oriented, not generic.
   Write one talking point per distinct risk category — do not bundle a
   technical concern and a commercial concern into the same bullet.
   If `ticket_count_last_90d` is 0, do not write a talking point that
   instructs reviewing open tickets or the support queue.

If ticket_count_last_90d is 0 and verified_risks is empty, say explicitly
that there has been no recent ticket activity to review rather than
inventing content to fill the section.
Return a single JSON object matching the required schema exactly.
"""


def build_synthesize_payload(account: dict, verified_risks: list[dict], ticket_count_last_90d: int) -> dict:
    return {
        "account": account,
        "verified_risks": verified_risks,
        "ticket_count_last_90d": ticket_count_last_90d,
    }
