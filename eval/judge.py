"""LLM-as-judge scoring."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import GEMINI_JUDGE_MODEL
from app.llm_client import generate_structured

JUDGE_PROMPT_VERSION = "judge_v1"

JUDGE_SYSTEM_PROMPT = """\
You are grading one output from an AI support/TAM tool against a specific
rubric. Read the rubric carefully — it already describes what a 1.0 and a
0.0 look like for this exact case. Do not apply generic quality standards
beyond what the rubric asks. Be strict: only score 1.0 if the output fully
satisfies what the rubric asks for.
"""


class JudgeScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    explanation: str


def judge_output(*, rubric: str, produced_output: dict) -> dict:
    raw = generate_structured(
        prompt_version=JUDGE_PROMPT_VERSION,
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_payload={"rubric": rubric, "produced_output": produced_output},
        response_schema=JudgeScore,
        model=GEMINI_JUDGE_MODEL,
        temperature=0,
    )
    return JudgeScore(**raw).model_dump()
