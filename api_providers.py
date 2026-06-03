"""
API Provider 抽象层：支持多 AI 服务商。
每个 Provider 实现 call(prompt) → str。
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 通用请求头 / Payload 结构（OpenAI 兼容格式）
# ---------------------------------------------------------------------------


@dataclass
class ApiConfig:
    """单个 AI 的 API 配置。"""
    provider: str          # "deepseek" | "openai" | "zhipu" | "minimax"
    api_key: str
    base_url: str          # 如 "https://api.deepseek.com"
    model: str             # 如 "deepseek-chat"


DEFAULT_PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "endpoint": "/chat/completions",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com",
        "model": "gpt-4o-mini",
        "endpoint": "/v1/chat/completions",
    },
    "zhipu": {
        "name": "智谱 AI（GLM）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "endpoint": "/chat/completions",
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v",
        "model": "MiniMax-Text-01",
        "endpoint": "/text/chatcompletion_v2",
    },
}


def build_api_config(provider: str, api_key: str, model: str | None = None) -> ApiConfig:
    """用已知的 Provider 信息构建 ApiConfig。"""
    p = DEFAULT_PROVIDERS.get(provider, DEFAULT_PROVIDERS["deepseek"])
    return ApiConfig(
        provider=provider,
        api_key=api_key,
        base_url=p["base_url"],
        model=model or p["model"],
    )


class BaseProvider(ABC):
    """API Provider 基类。"""

    def __init__(self, config: ApiConfig) -> None:
        self.config = config

    @abstractmethod
    async def call(self, prompt: str) -> str | None:
        """发送 prompt，返回 AI 回复文本。出错返回 None。"""


# ---------------------------------------------------------------------------
# DeepSeek
# ---------------------------------------------------------------------------

class DeepSeekProvider(BaseProvider):
    async def call(self, prompt: str) -> str | None:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        url = f"{self.config.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


# ---------------------------------------------------------------------------
# OpenAI（兼容格式）
# ---------------------------------------------------------------------------

class OpenAIProvider(BaseProvider):
    async def call(self, prompt: str) -> str | None:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        url = f"{self.config.base_url}/v1/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


# ---------------------------------------------------------------------------
# 智谱（GLM）
# ---------------------------------------------------------------------------

class ZhipuProvider(BaseProvider):
    async def call(self, prompt: str) -> str | None:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        url = f"{self.config.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


# ---------------------------------------------------------------------------
# MiniMax
# ---------------------------------------------------------------------------

class MiniMaxProvider(BaseProvider):
    async def call(self, prompt: str) -> str | None:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        url = f"{self.config.base_url}/text/chatcompletion_v2"
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Provider 工厂
# ---------------------------------------------------------------------------

_PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "deepseek": DeepSeekProvider,
    "openai":   OpenAIProvider,
    "zhipu":    ZhipuProvider,
    "minimax":  MiniMaxProvider,
}


def create_provider(config: ApiConfig) -> BaseProvider | None:
    cls = _PROVIDER_CLASSES.get(config.provider)
    if cls is None:
        return None
    return cls(config)


def provider_display_name(provider: str) -> str:
    return DEFAULT_PROVIDERS.get(provider, {}).get("name", provider)


def all_providers() -> dict[str, str]:
    """返回 {provider_id: display_name, ...}."""
    return {k: v["name"] for k, v in DEFAULT_PROVIDERS.items()}
