"""嵌入层：本地 / 云端 / 开发兜底。

- LocalEmbedder：优先 sentence-transformers；不可用时降级到 HashEmbedder（确定性、零依赖）。
- CloudEmbedder：OpenAI 兼容 /embeddings 端点。
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

from .config import Settings


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class Embedder:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def dim(self) -> int:
        raise NotImplementedError


class HashEmbedder(Embedder):
    """确定性兜底嵌入：无需下载权重，适合开发 / 单测 / 无网环境。

    把每个 token 哈希到维度槽位并累加，再 L2 归一化。
    相同文本 → 相同向量（满足可复现不变量）。
    """

    def __init__(self, dim: int = 512):
        self._dim = dim

    def dim(self) -> int:
        return self._dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self._dim
            for tok in _tokenize(text):
                h = int.from_bytes(hashlib.md5(tok.encode("utf-8")).digest()[:4], "big")
                vec[h % self._dim] += 1.0
            # L2 归一化
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            out.append(vec)
        return out


class LocalEmbedder(Embedder):
    def __init__(self, model_name: str, dim: int = 512):
        self.model_name = model_name
        self._dim = dim
        self._model = None
        self._fallback = None

    def _load(self):
        if self._model is not None or self._fallback is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._dim = self._model.get_sentence_embedding_dimension()
        except Exception:
            # 无权重 / 无网络 → 确定性兜底
            self._fallback = HashEmbedder(self._dim)

    def dim(self) -> int:
        self._load()
        return self._dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        self._load()
        if self._model is not None:
            vecs = self._model.encode(texts, normalize_embeddings=True)
            return [list(map(float, v)) for v in vecs]
        return self._fallback.embed(texts)


class CloudEmbedder(Embedder):
    def __init__(self, base_url: str, api_key: str, model: str, dim: int = 1536):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._dim = dim

    def dim(self) -> int:
        return self._dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        import httpx

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return [list(map(float, d["embedding"])) for d in data]


def build_embedder(settings: Settings) -> Embedder:
    if settings.embed_provider == "cloud" and settings.cloud_llm_base_url:
        return CloudEmbedder(
            settings.cloud_llm_base_url,
            settings.cloud_llm_api_key,
            settings.cloud_llm_model or settings.embed_model,
        )
    return LocalEmbedder(settings.embed_model, settings.embed_dim)
