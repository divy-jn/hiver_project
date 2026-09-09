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
RANDOM_SEED = 42

# ── LLM ───────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
OPENAI_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
OPENAI_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", None))

# ── Embedding model ──────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Pipeline defaults ────────────────────────────────────────────────
MAX_BRAND_SAMPLE = 50_000       # max tweets to load per brand for profiling
GOLDEN_SET_SIZE = 200           # target golden-set examples
RETRIEVAL_TOP_K = 5             # top-k for retrieval
TARGET_INTENTS = (6, 12)        # min/max intents to discover

# ── Escalation thresholds ────────────────────────────────────────────
ESCALATION_CONFIDENCE_THRESHOLD = 0.4    # classify confidence below this → escalate
RETRIEVAL_SCORE_THRESHOLD = 0.3          # retrieval score below this → escalate

# ── LLM call settings ────────────────────────────────────────────────
LLM_TEMPERATURE = 0.0
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 30

def ensure_dirs():
    """Create all output directories."""
    for d in [DATA_RAW, DATA_PROCESSED, DATA_GOLDEN, REPORTS, FIGURES, TABLES, PROMPTS]:
        d.mkdir(parents=True, exist_ok=True)
