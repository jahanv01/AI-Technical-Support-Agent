"""Central config: env vars, paths, and generation defaults.

Everything that affects determinism or output shape should be read from here,
not hardcoded in individual modules, so eval and prod use identical settings.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
KB_DIR = ROOT_DIR / "knowledge-base"
CACHE_DIR = ROOT_DIR / ".cache"

TICKETS_PATH = DATA_DIR / "tickets.json"
ACCOUNTS_PATH = DATA_DIR / "accounts.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_JUDGE_MODEL = os.environ.get("GEMINI_JUDGE_MODEL", "gemini-3.5-flash-lite")
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0"))

# Account-brief "last 90 days" is computed relative to this fixed date rather
# than datetime.now(), so results don't silently change day to day. Set to
# the max created_at seen in tickets.json at load time — see account_brief.py.
ACCOUNT_BRIEF_LOOKBACK_DAYS = 90

# KB retrieval: with only 85 chunks and no stopword filtering, BM25 alone
# isn't precise enough to be the sole gate (verified empirically — see
# retrieval.py's docstring). This threshold just filters pure noise; the
# triage prompt itself makes the final relevance call before citing
# matched_kb_doc (two-stage: BM25 for recall, LLM for precision).
KB_MATCH_SCORE_THRESHOLD = 5.0

# Triage confidence: below this, set needs_human_review=True instead of
# guessing a tier.
TRIAGE_CONFIDENCE_THRESHOLD = 0.5  # TODO: tune

PRODUCT_AREAS = [
    # TODO: fill in from the real tickets.json / knowledge-base contents,
    # e.g. "Connectors", "Authentication", "Reporting", ...
]

ISSUE_CATEGORIES = [
    "Bug",
    "Feature Request",
    "How-To",
    "Performance",
    "Billing",
    "Integration",
    "Onboarding",
    "Data Loss",
]

URGENCY_TIERS = ["P1", "P2", "P3", "P4"]
