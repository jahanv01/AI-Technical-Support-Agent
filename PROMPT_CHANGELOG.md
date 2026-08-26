# Prompt Changelog

Each prompt module in `app/prompts/` exports a `VERSION` string used as the
eval/cache key, so scoring stays attributable to a specific prompt revision.

## triage_v1
- Initial version. Classifies product_area/issue_category/urgency_tier with
  reasoning, optional KB match, and a confidence-gated human-review fallback.

## account_brief_v1
- Initial version. Two-call chain: (1) extract quote-grounded candidate risk
  signals from tickets + escalation_notes, (2) synthesize the 3-section brief.
