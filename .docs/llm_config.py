from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env.local", override=False)

# 只改这里即可切换默认环境：bailian / local / openai
ACTIVE_ENV = "bailian"

ENV_CONFIGS: dict[str, dict] = {
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-1ea33e59d2704e31be3632213be61118",
        "model": "qwen-plus",
        "temperature": 0.0,
    },
    "local": {
        "base_url": "http://127.0.0.1:1234/v1",
        "api_key": "not-needed",
        "model": "qwen3",
        "temperature": 0.0,
    },
    "openai": {
        "base_url": None,  # OpenAI 官方端点，不设置 base_url
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
    },
}


def _normalize_env(env: str) -> str:
    normalized = env.lower().strip()
    if normalized not in ENV_CONFIGS:
        supported = ", ".join(ENV_CONFIGS.keys())
        raise ValueError(f"Unsupported env '{env}', supported: {supported}")
    return normalized


def llm_config(
    env: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> dict:
    normalized_env = _normalize_env(env or ACTIVE_ENV)
    config = dict(ENV_CONFIGS[normalized_env])
    if model is not None:
        config["model"] = model
    if temperature is not None:
        config["temperature"] = float(temperature)
    return config


def build_chat_openai(
    env: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    **kwargs,
) -> ChatOpenAI:
    config = llm_config(env=env, model=model, temperature=temperature)
    if config.get("base_url"):
        return ChatOpenAI(**config, **kwargs)
    return ChatOpenAI(
        model=config["model"],
        api_key=config["api_key"],
        temperature=config["temperature"],
        **kwargs,
    )


def lmstudio_config(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> dict:
    # 兼容旧调用名，实际返回当前环境配置
    return llm_config(env=provider, model=model, temperature=temperature)
