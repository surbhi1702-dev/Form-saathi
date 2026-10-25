"""Runtime settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path = BASE_DIR.parent / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    # Groq model names change over time - override them in .env if one is retired.
    chat_model: str = field(default_factory=lambda: os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile"))
    vision_model: str = field(
        default_factory=lambda: os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    )
    # Optional: a free Google Gemini key (https://aistudio.google.com/apikey) for reading photos of forms.
    # Used instead of a Groq vision model when set. Leave the model empty to pick one automatically.
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_vision_model: str = field(default_factory=lambda: os.getenv("GEMINI_VISION_MODEL", ""))
    # Optional: URL of your fine-tuned jargon simplifier (finetune/serve_simplifier.py)
    simplifier_url: str = field(default_factory=lambda: os.getenv("SIMPLIFIER_URL", ""))
    # Force the offline mock LLM (used by tests and when no key is set)
    force_mock: bool = field(default_factory=lambda: _bool("FORMSAATHI_MOCK_LLM"))
    session_ttl_minutes: int = field(default_factory=lambda: int(os.getenv("SESSION_TTL_MINUTES", "30")))
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    )
    # Stamp duty / registration fee used by the registration-deed estimate (percent of value).
    # These differ by state and change - always verify the current rate.
    stamp_duty_percent: float = field(default_factory=lambda: float(os.getenv("STAMP_DUTY_PERCENT", "7")))
    registration_fee_percent: float = field(
        default_factory=lambda: float(os.getenv("REGISTRATION_FEE_PERCENT", "2"))
    )

    @property
    def use_mock(self) -> bool:
        return self.force_mock or not self.groq_api_key


def get_settings() -> Settings:
    return Settings()
