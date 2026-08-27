"""Thin Gemini wrapper: structured-JSON calls + a response cache for determinism.

Uses the current `google-genai` SDK (the older `google-generativeai` package
is fully deprecated as of 2025 — no bug fixes, no updates).

The cache is what actually *guarantees* Task 2's determinism requirement
(temperature=0 alone narrows but doesn't guarantee bit-identical output) — it
keys on a hash of (prompt_version, system_prompt, canonicalized input), so
editing a prompt's wording (even without bumping its VERSION) invalidates
old cache entries instead of silently replaying stale classifications.
Stores to CACHE_DIR as JSON, and is always checked before calling the API.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Type

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.config import CACHE_DIR, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE

CACHE_DIR.mkdir(exist_ok=True)

_client: genai.Client | None = None


REQUEST_TIMEOUT_MS = 30_000  # fail fast instead of hanging indefinitely on a stalled connection

# Free-tier Gemini enforces GenerateRequestsPerMinutePerProjectPerModel = 5.
# Running eval cases concurrently (see eval/run_eval.py's thread pool) blew
# straight through that in a single burst and 429'd almost everything, so
# rate-limiting has to live here in the shared client, not in each caller.
RATE_LIMIT_PER_MINUTE = 4  # slightly under the observed cap of 5, as headroom
_call_times: deque[float] = deque()
_rate_lock = threading.Lock()


def _wait_for_rate_limit() -> None:
    while True:
        with _rate_lock:
            now = time.monotonic()
            while _call_times and now - _call_times[0] > 60:
                _call_times.popleft()
            if len(_call_times) < RATE_LIMIT_PER_MINUTE:
                _call_times.append(now)
                return
            sleep_for = 60 - (now - _call_times[0]) + 0.1
        time.sleep(sleep_for)


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
    return _client


def _cache_key(prompt_version: str, system_prompt: str, payload: dict[str, Any]) -> str:
    blob = json.dumps(
        {"prompt_version": prompt_version, "system_prompt": system_prompt, "payload": payload},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def generate_structured(
    *,
    prompt_version: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    response_schema: Type[BaseModel],
    model: str = GEMINI_MODEL,
    temperature: float = GEMINI_TEMPERATURE,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Call Gemini and return parsed JSON matching response_schema.

    Caller is responsible for re-validating the returned dict through the
    actual Pydantic model (cheap insurance against schema drift the API
    might still let through).
    """
    key = _cache_key(prompt_version, system_prompt, user_payload)
    cache_file = _cache_path(key)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))["response"]

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=response_schema,
    )

    start = time.perf_counter()
    max_attempts = 3  # bounded: 30s request timeout + short sleeps, worst case is a few minutes, not indefinite
    for attempt in range(1, max_attempts + 1):
        _wait_for_rate_limit()
        try:
            result = client.models.generate_content(model=model, contents=json.dumps(user_payload), config=config)
            break
        except genai_errors.ClientError as e:
            # Daily quota exhaustion is not retryable — fail immediately rather
            # than burning 3 attempts × 18 s on calls that will all be rejected.
            if e.code == 429 and "PerDay" in str(e):
                raise
            # Per-minute rate limit: honor the API's retryDelay.
            if e.code == 429 and attempt < max_attempts:
                match = re.search(r"'retryDelay': '([\d.]+)s'", str(e))
                time.sleep(float(match.group(1)) + 0.5 if match else 15.0)
                continue
            raise
        except (genai_errors.ServerError, TimeoutError, ConnectionError, httpx.TimeoutException):
            # Transient 503s under load, or a stalled connection (now raises
            # instead of hanging thanks to the request timeout above).
            if attempt == max_attempts:
                raise
            time.sleep(2 ** attempt)
    latency_s = time.perf_counter() - start

    if not result.candidates:
        raise RuntimeError(f"Gemini returned no candidates (likely safety-blocked) for prompt_version={prompt_version}")

    response = json.loads(result.text)
    usage = {
        "latency_s": round(latency_s, 3),
        "prompt_tokens": result.usage_metadata.prompt_token_count,
        "output_tokens": result.usage_metadata.candidates_token_count,
    }

    if use_cache:
        cache_file.write_text(json.dumps({"response": response, "usage": usage}, indent=2), encoding="utf-8")

    return response
