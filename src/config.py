"""Centralized configuration for the Hiver SDE Intern project."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_GOLDEN = ROOT / "data" / "golden"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
PROMPTS = ROOT / "prompts"

RAW_CSV = DATA_RAW / "twcs.csv"

# ── Reproducibility ───────────────────────────────────────────────────
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

# ── LLM ───────────────────────────────────────────────────────────────
# Provider-agnostic names are preferred. OPENAI_* remain supported so the
# project can also run directly against the standard OpenAI endpoint.
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
if not LLM_API_KEY:
    raise ValueError("Missing required environment variable: LLM_API_KEY (or OPENAI_API_KEY)")

LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", None))

# Backward-compatible aliases for existing imports in the codebase.
OPENAI_API_KEY = LLM_API_KEY
OPENAI_MODEL = LLM_MODEL
OPENAI_BASE_URL = LLM_BASE_URL

# ── Embedding model ──────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── Pipeline defaults ────────────────────────────────────────────────
MAX_BRAND_SAMPLE = int(os.getenv("MAX_BRAND_SAMPLE", "50000"))
GOLDEN_SET_SIZE = int(os.getenv("GOLDEN_SET_SIZE", "200"))
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
TARGET_INTENTS = (8, 10)

# ── Escalation thresholds ────────────────────────────────────────────
ESCALATION_CONFIDENCE_THRESHOLD = float(
    os.getenv("ESCALATION_CONFIDENCE_THRESHOLD", "0.4")
)
RETRIEVAL_SCORE_THRESHOLD = float(
    os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.3")
)

# ── LLM call settings ────────────────────────────────────────────────
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))


def ensure_dirs() -> None:
    """Create all output directories."""
    for directory in [
        DATA_RAW,
        DATA_PROCESSED,
        DATA_GOLDEN,
        REPORTS,
        FIGURES,
        TABLES,
        PROMPTS,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def require_llm_credentials() -> None:
    """Fail fast with a clear message when an LLM key is required but missing."""
    if not LLM_API_KEY:
        raise RuntimeError(
            "Missing LLM_API_KEY. Copy .env.example to .env and set LLM_API_KEY "
            "for your OpenAI-compatible endpoint."
        )
