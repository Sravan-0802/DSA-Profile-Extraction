"""Application configuration loaded from environment / .env."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env sitting next to the backend/ root (one level above app/).
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
INTERNAL_PROJECT_LIST_PATH = RESOURCES_DIR / "INTERNAL_PROJECT_LIST.txt"


def _collect_mistral_keys() -> list[str]:
    """Gather Mistral keys from MISTRAL_API_KEY and MISTRAL_API_KEY_1..N."""
    keys: list[str] = []
    single = os.getenv("MISTRAL_API_KEY", "").strip()
    if single:
        keys.append(single)
    for i in range(1, 13):  # support up to 12 numbered keys
        val = os.getenv(f"MISTRAL_API_KEY_{i}", "").strip()
        if val:
            keys.append(val)
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def _collect_github_tokens() -> list[str]:
    """Gather GitHub tokens from GITHUB_TOKEN and GITHUB_TOKEN_1..N.

    Tokens raise the GitHub API rate limit from 60/hr (anonymous) to
    5000/hr each, which the GitHub Analysis mode needs since it makes many
    API calls per candidate. Multiple tokens are used round-robin.
    """
    keys: list[str] = []
    single = os.getenv("GITHUB_TOKEN", "").strip()
    if single:
        keys.append(single)
    for i in range(1, 13):
        val = os.getenv(f"GITHUB_TOKEN_{i}", "").strip()
        if val:
            keys.append(val)
    seen: set[str] = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


class Settings:
    def __init__(self) -> None:
        self.mistral_keys: list[str] = _collect_mistral_keys()
        self.github_tokens: list[str] = _collect_github_tokens()
        self.mistral_model: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
        self.default_concurrency: int = int(os.getenv("DEFAULT_CONCURRENCY", "8"))
        self.max_concurrency: int = int(os.getenv("MAX_CONCURRENCY", "20"))
        self.enable_ocr: bool = os.getenv("ENABLE_OCR", "true").lower() in ("1", "true", "yes")
        self.tesseract_cmd: str = os.getenv("TESSERACT_CMD", "").strip()
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if o.strip()
        ]

    @property
    def has_ai(self) -> bool:
        return len(self.mistral_keys) > 0

    @property
    def has_github(self) -> bool:
        return len(self.github_tokens) > 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
