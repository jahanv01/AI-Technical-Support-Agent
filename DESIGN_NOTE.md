# Design Note

## Failure modes

**1. Hallucinated KB citation.** With only ~85 KB chunks and no stopword filtering, BM25 retrieval alone isn't precise enough to trust as the sole gate — a long chunk with several loosely-overlapping generic words can occasionally outrank a short, exactly-relevant one. Mitigated with a two-stage design: BM25 surfaces up to 2 candidates (recall), the triage prompt is given only those candidates' exact breadcrumb headings as the *allowed* values for `matched_kb_doc`, and `app/triage.py` re-checks in code afterward that whatever the model returned is actually one of the candidates offered — nulling it out otherwise even if the model ignores the prompt instruction. Detected in eval via the adversarial case (`triage_case_06`) asserting `matched_kb_doc_is_null` on an unclassifiable ticket.

**2. Non-deterministic Task 2 output.** `temperature=0` narrows but doesn't guarantee bit-identical output across runs. Mitigated with a response cache in `app/llm_client.py` keyed on `(prompt_version, canonicalized input)` — the same account/ticket set always replays the exact stored response rather than calling the API again. Verifiable by diffing two runs on the same `account_id`.

**3. Rate-limit/quota exhaustion causing silent stalls.** This wasn't hypothetical — it happened during this build. The free-tier Gemini API enforces 4-5 requests/minute per model, and running eval cases concurrently without any client-side throttling caused a cascade of 429s; separately, an unconfigured HTTP client with no request timeout let one stalled call hang for over an hour with no error surfaced at all. Both are now handled in `app/llm_client.py`: a token-bucket rate limiter shared across threads keeps calls under the observed cap, a 30-second request timeout guarantees a call fails fast instead of hanging, and 429 responses are retried using the server's own suggested `retryDelay` rather than a blind backoff. This is exactly the kind of failure that's invisible in a single-request demo and only shows up under any real concurrent load — worth treating as a first-class case, not an edge case.

## Latency vs quality

Task 2 uses a **two-call prompt chain** (extract candidate risk signals from tickets/escalation notes → synthesize the 3-section brief) instead of one mega-prompt. Slower — two round-trips instead of one — but each step is independently checkable: quote-grounding is verified in code between the two calls, so an ungrounded candidate never reaches the final brief, rather than hoping the model self-polices in a single pass.

Under a hard latency constraint, the first cut would be collapsing this to one call with the schema asking for both extraction and synthesis at once, accepting weaker quote-grounding guarantees. The LLM-judge in the eval harness would also move fully offline (CI/regression only) rather than any part of a live path — it's not on the product's critical path today, but it's the first thing to explicitly exclude if latency became the constraint.

## Data sensitivity

Ticket and account text may contain PII (emails, phone numbers embedded in ticket bodies). `app/pii.py` applies a regex-based redaction pass (emails, phone numbers) to `subject`/`body`/`escalation_notes` text before it enters `user_payload` in both `app/triage.py` and `app/account_brief.py` — the only points where raw customer text leaves the process. Redaction happens *before* caching too, since `app/llm_client.py` persists API responses to disk in `.cache/`, so no raw PII is retained there either. Quote-grounding checks (`eval/rules.py`, and the same guard inline in `account_brief.py`) still compare against the *original* unredacted ticket body — safe in practice, since a genuine churn-signal quote is vanishingly unlikely to itself be someone's email or phone number.

This is intentionally narrow (two regex patterns, not a general PII classifier) and doesn't cover names or free-text identifying details — a fuller implementation would need a proper NER-based redaction step. Since this dataset is fully synthetic, no real PII is actually at risk today; the pattern (redact-before-send, redact-before-cache) is what would matter immediately with real customer data.

## Scaling 10×

Two things break first, in order:

1. **The free-tier rate limit, immediately** — not a 10× problem, a *today* problem. At 4-5 requests/minute, even this project's own 12-case eval suite takes several minutes; 10× ticket volume with live (uncached) triage calls would queue almost entirely behind the rate limiter. This is the actual first bottleneck, ahead of anything architectural, and the fix is unglamorous: a paid tier with a real RPM budget, not a code change.
2. **BM25 index rebuild time**, if `KBIndex.build()` were ever called per-request instead of once at startup (it currently isn't — `app/triage.py` builds it once as a module-level singleton). At 10× KB size this would still be fast in-memory, but it's the next thing to watch if the KB corpus grows much larger than a few hundred chunks.

The eval harness's LLM-judge calls also scale linearly with test case count and would need sampling (grade a subset per commit, full suite on a schedule) rather than every case on every push once the suite grows past a few dozen cases.
