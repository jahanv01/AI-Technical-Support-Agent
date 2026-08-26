# Design Note

_Draft skeleton — expand each bullet into prose in your own words before submitting (~600 words total, roughly one short paragraph per section). These points are grounded in decisions actually made in this codebase, not generic answers._

## Failure modes

Top 3 candidates, each with how this design detects/mitigates it:

1. **Hallucinated KB citation** — the model claims a `matched_kb_doc` that isn't actually relevant. Mitigated by gating `matched_kb_doc` on the BM25 retrieval score clearing `KB_MATCH_SCORE_THRESHOLD` (`app/config.py`) rather than letting the model name a doc freely — detection is a rule-based eval check (`matched_kb_doc_is_null` in `eval/rules.py`).
2. **Non-deterministic Task 2 output despite `temperature=0`** — Gemini's temperature=0 narrows but doesn't guarantee bit-identical output. Mitigated by the response cache in `app/llm_client.py`, keyed on `(prompt_version, canonicalized input)` — same account/ticket set always returns the exact stored response. Detect drift by diffing two runs on the same account_id.
3. **Silent schema drift** — malformed/incomplete JSON from the model breaks downstream consumers silently. Mitigated by forcing `response_schema` at the API call and validating through Pydantic (`app/schemas.py`), which raises loudly instead of passing bad data through — caught immediately by `eval/run_eval.py`'s exception handling per case.

(Optional 4th, if you built the confidence/fallback path: silently-wrong classification on ambiguous tickets — mitigated by `needs_human_review` gating in `app/triage.py`, exercised by the adversarial eval case `triage_case_06`.)

## Latency vs quality

Concrete trade-off actually made: Task 2 uses a **two-call prompt chain**
(extract candidate risk signals → synthesize the 3-section brief) instead of
one mega-prompt. Slower (2 round-trips) and more expensive, but each step is
independently gradable and the quote-grounding check can run between the two
calls rather than only after the fact.

What you'd change under a hard latency constraint: collapse to a single call
with the schema asking for both extraction and synthesis at once; drop the
LLM-judge from the online path entirely (keep it for offline/CI regression
only, where latency doesn't matter); rely on the rule-based checks and the
response cache for online quality/speed.

## Data sensitivity

Tickets/accounts may contain PII (contact names, emails embedded in ticket
bodies, etc). [Note: state here whether you implemented the PII-redaction
pass from the plan — a regex-based scrub of emails/phone numbers before any
text is sent to the Gemini API — or, if not, that this is the identified gap
and what you'd add first.] Also note: this is a synthetic dataset, so this
section is a design demonstration of the *pattern* (redact-before-send,
never log raw PII, cache keys are hashed not plaintext) rather than a live
compliance claim.

## Scaling 10×

At 10× ticket volume (5,000 tickets), the first thing to break is **BM25
index rebuild time** in `app/retrieval.py` if it's rebuilt from scratch per
request rather than built once and reused — fix: build once at startup,
persist/incrementally update rather than rebuild per call. Second: the
**LLM-judge in the eval harness** scales linearly with case count and API
cost/latency — fine at today's 12 cases, not fine if the suite grows with
the data; fix: sample a subset for judge-scoring on every commit, run the
full judge suite only on a schedule or before release.
