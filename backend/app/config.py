"""Application configuration from environment variables."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent  # plum/
POLICY_TERMS_PATH = PROJECT_ROOT / "policy_terms.json"
TEST_CASES_PATH = PROJECT_ROOT / "test_cases.json"
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "claims.db"

# LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Ensure dirs exist
UPLOADS_DIR.mkdir(exist_ok=True)
