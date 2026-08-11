"""Mistral AI client with exponential-backoff retries."""
from __future__ import annotations

import json
import logging
import random
import time

import requests

from ..config import get_settings

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
_SYSTEM_PROMPT = (
    "You are an expert resume parser and data analyst. Always return STRICT "
    "JSON only—no markdown fences, no commentary. Fill missing values with "
    'empty strings "" or [] where appropriate.'
)


def analyze_text_with_mistral(prompt: str, api_key: str) -> str:
    """Call Mistral chat completions; returns the raw content string.

    On persistent failure returns a JSON string with an "error" key so the
    caller's JSON parsing path handles it uniformly.
    """
    if not api_key:
        return json.dumps({"error": "Missing Mistral API key for this request."})

    settings = get_settings()
    key_id = f"...{api_key[-4:]}" if len(api_key) > 4 else "key"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.mistral_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    attempts = 5
    initial_backoff = 2.0
    for attempt in range(attempts):
        try:
            resp = requests.post(_ENDPOINT, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return content.strip()
            if resp.status_code == 429 or resp.status_code in (500, 502, 503, 504):
                wait = initial_backoff * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Mistral %s on key %s (attempt %d/%d); retrying in %.1fs",
                    resp.status_code, key_id, attempt + 1, attempts, wait,
                )
                time.sleep(wait)
                continue
            logger.error("Mistral API error on key %s: %s - %s", key_id, resp.status_code, resp.text[:300])
            return json.dumps({"error": f"API Error {resp.status_code}"})
        except requests.RequestException as exc:
            wait = initial_backoff * (2 ** attempt) + random.uniform(0, 1)
            logger.warning("Mistral request error on key %s: %s; retrying in %.1fs", key_id, exc, wait)
            time.sleep(wait)

    return json.dumps({"error": "API request failed after all retries."})
