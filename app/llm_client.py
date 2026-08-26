"""Thin Gemini wrapper: structured-JSON calls + a response cache for determinism.

TODO(you): implement generate_structured() using google.generativeai, with
response_mime_type="application/json" and a response_schema derived from the
target Pydantic model, at config.GEMINI_TEMPERATURE.

The cache is what actually *guarantees* Task 2's determinism requirement
(temperature=0 alone narrows but doesn't guarantee bit-identical output) — key
it on a hash of (prompt_version, canonicalized input), store to CACHE_DIR as
JSON, and always check it before calling the API.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from app.config import CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE

CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(prompt_version: str, payload: dict[str, Any]) -> str:
    blob = json.dumps({"prompt_version": prompt_version, "payload": payload}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def generate_structured(
    *,
    prompt_version: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    response_schema: dict[str, Any],
    model: str = GEMINI_MODEL,
    temperature: float = GEMINI_TEMPERATURE,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Call Gemini and return parsed+validated JSON matching response_schema.

    Also records token usage + latency alongside the cached response so
    eval/run_eval.py can report average cost/latency per call.
    """
    key = _cache_key(prompt_version, user_payload)
    cache_file = _cache_path(key)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))["response"]

    # TODO(you):
    #   import google.generativeai as genai
    #   genai.configure(api_key=GEMINI_API_KEY)
    #   gen_model = genai.GenerativeModel(model)
    #   start = time.perf_counter()
    #   result = gen_model.generate_content(
    #       [system_prompt, json.dumps(user_payload)],
    #       generation_config={
    #           "temperature": temperature,
    #           "response_mime_type": "application/json",
    #           "response_schema": response_schema,
    #       },
    #   )
    #   latency_s = time.perf_counter() - start
    #   response = json.loads(result.text)
    #   usage = {"latency_s": latency_s, "prompt_tokens": ..., "output_tokens": ...}
    #   if use_cache:
    #       cache_file.write_text(json.dumps({"response": response, "usage": usage}, indent=2))
    #   return response
    raise NotImplementedError("Wire up the Gemini call here.")
