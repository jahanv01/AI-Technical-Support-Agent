# Prompt Changelog

Each prompt module in `app/prompts/` exports a `VERSION` string used as the
eval/cache key, so scoring stays attributable to a specific prompt revision.

## triage_v1
- Initial version. Classifies product_area/issue_category/urgency_tier with
  reasoning, optional KB match, and a confidence-gated human-review fallback.

## account_brief_v1
- Initial version. Two-call chain: (1) extract quote-grounded candidate risk
  signals from tickets + escalation_notes, (2) synthesize the 3-section brief.

## account_brief_v2
- Extract step: explicitly instructs that every non-empty `escalation_notes`
  entry is a pre-vetted signal to surface by default, not something to weigh
  for "genuineness" — fixes an observed case where the model substituted a
  ticket-based signal for an explicit escalation note instead of including
  both.
- Synthesize step: talking_points must name a specific action, not a vague
  topic to "discuss" — fixes generic, non-actionable talking points observed
  on a commercial/pricing-risk account.

## account_brief_v3
- Synthesize step: explicitly states that `account.open_tickets` /
  `p1_tickets_last_30d` are a stale/unverified snapshot and
  `ticket_count_last_90d` is authoritative — fixes an observed case where the
  model stated specific recent-ticket claims sourced from the stale account
  field despite the verified 90-day ticket count being zero (caught by the
  adversarial sparse-data eval case).
