from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "salesforge.db"


def get_secret(name: str, default: str = "") -> str:
    """Read a secret from Streamlit secrets first, then environment variables."""
    if st is not None:
        try:
            value: Any = st.secrets.get(name, default)  # type: ignore[attr-defined]
            if value is not None:
                return str(value)
        except Exception:
            pass
    return os.getenv(name, default)


@dataclass(frozen=True)
class AISettings:
    api_key: str
    model_scoring: str
    model_creative: str
    model_fast: str

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())


def ai_settings() -> AISettings:
    return AISettings(
        api_key=get_secret("OPENROUTER_API_KEY", ""),
        model_scoring=get_secret("OPENROUTER_MODEL_SCORING", "google/gemini-flash-1.5"),
        model_creative=get_secret("OPENROUTER_MODEL_CREATIVE", "anthropic/claude-3.5-sonnet"),
        model_fast=get_secret("OPENROUTER_MODEL_FAST", "openai/gpt-4o-mini"),
    )
