"""LLM-as-judge scoring.

TODO(you): implement judge_output(). Call llm_client.generate_structured()
(or a dedicated Gemini call at config.GEMINI_JUDGE_MODEL, temperature=0) with
a fixed judge system prompt + the case's `judge_rubric` + the produced
output, asking for {"score": 0.0-1.0, "explanation": str}.

Keep the judge prompt itself version-pinned (JUDGE_PROMPT_VERSION below) so a
prompt change is visible in eval history, same as the product prompts.
"""
from __future__ import annotations

JUDGE_PROMPT_VERSION = "judge_v1"

JUDGE_SYSTEM_PROMPT = """\
You are grading one output from an AI support/TAM tool against a specific
rubric. Read the rubric carefully — it already describes what a 1.0 and a
0.0 look like for this exact case. Do not apply generic quality standards
beyond what the rubric asks.

Return a JSON object: {"score": <float 0.0-1.0>, "explanation": "<one sentence>"}
"""


def judge_output(*, rubric: str, produced_output: dict) -> dict:
    """Return {"score": float, "explanation": str}."""
    raise NotImplementedError
