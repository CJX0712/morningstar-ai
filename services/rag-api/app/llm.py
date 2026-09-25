"""大模型客户端：本地（llama.cpp / OpenAI 兼容）+ 云端兜底。

FallbackLLM 先打本地，失败/超时自动降级到云端（若已配置）。
"""
from __future__ import annotations

from typing import AsyncGenerator, List, Optional

import httpx

from .config import Settings


class LLMClient:
    def __init__(self, base_url: str, api_key: str = "", model: str = "local"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: List[dict], temperature: float = 0.7) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def stream(self, messages: List[dict], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json

                        delta = json.loads(data)["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue


class FallbackLLM:
    """主备 LLM：本地优先，云端兜底。"""

    def __init__(self, primary: LLMClient, secondary: Optional[LLMClient] = None):
        self.primary = primary
        self.secondary = secondary

    async def complete(self, messages: List[dict], temperature: float = 0.7) -> str:
        try:
            return await self.primary.complete(messages, temperature)
        except Exception:
            if self.secondary is not None:
                return await self.secondary.complete(messages, temperature)
            raise

    async def stream(self, messages: List[dict], temperature: float = 0.7) -> AsyncGenerator[str, None]:
        try:
            async for tok in self.primary.stream(messages, temperature):
                yield tok
        except Exception:
            if self.secondary is not None:
                async for tok in self.secondary.stream(messages, temperature):
                    yield tok
            else:
                raise


def build_llm(settings: Settings) -> FallbackLLM:
    primary = LLMClient(settings.llm_base_url, api_key="", model=settings.llm_model)
    secondary = None
    if settings.cloud_llm_base_url and settings.cloud_llm_api_key:
        secondary = LLMClient(
            settings.cloud_llm_base_url,
            api_key=settings.cloud_llm_api_key,
            model=settings.cloud_llm_model,
        )
    return FallbackLLM(primary, secondary)
