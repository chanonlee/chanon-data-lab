import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local", override=False)


def _as_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_chat_openai(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    **kwargs,
) -> ChatOpenAI:
    resolved_provider = (provider or os.environ.get("LM_PROVIDER", "lmstudio")).lower()

    if resolved_provider == "openai":
        return ChatOpenAI(
            model=model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=(
                temperature
                if temperature is not None
                else _as_float(os.environ.get("OPENAI_TEMPERATURE", "0"), 0.0)
            ),
            **kwargs,
        )

    return ChatOpenAI(
        base_url=os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
        api_key=os.environ.get("LM_STUDIO_API_KEY", "lm-studio"),
        model=model or os.environ.get("LM_STUDIO_MODEL", "local"),
        temperature=(
            temperature
            if temperature is not None
            else _as_float(os.environ.get("LM_STUDIO_TEMPERATURE", "0"), 0.0)
        ),
        **kwargs,
    )


def lmstudio_config(
    model: str | None = None,
    temperature: float | None = None,
) -> dict:
    return {
        "base_url": os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
        "api_key": os.environ.get("LM_STUDIO_API_KEY", "lm-studio"),
        "model": model or os.environ.get("LM_STUDIO_MODEL", "local"),
        "temperature": (
            temperature
            if temperature is not None
            else _as_float(os.environ.get("LM_STUDIO_TEMPERATURE", "0"), 0.0)
        ),
    }
