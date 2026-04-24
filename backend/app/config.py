"""Application configuration from environment variables."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent  # plum/

# policy_terms.json lives in backend/ (copy) and project root (original).
# Prefer backend/ so Railway deployments with root-dir=backend work without extra config.
def _find_file(name: str) -> Path:
    for candidate in (BASE_DIR / name, PROJECT_ROOT / name):
        if candidate.exists():
            return candidate
    return BASE_DIR / name  # let callers surface a clear FileNotFoundError

POLICY_TERMS_PATH = Path(os.getenv("POLICY_TERMS_PATH", str(_find_file("policy_terms.json"))))
TEST_CASES_PATH = Path(os.getenv("TEST_CASES_PATH", str(_find_file("test_cases.json"))))
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "claims.db"

# LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Ensure dirs exist
UPLOADS_DIR.mkdir(exist_ok=True)
