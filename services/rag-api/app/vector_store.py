"""向量存储：Qdrant 优先，连接失败时降级为内存存储。"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .config import Settings


def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._memory: Dict[str, Tuple[List[float], dict]] = {}
        self._try_qdrant()

    def _try_qdrant(self):
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self.settings.qdrant_url, timeout=3)
            self._client.get_collections()
        except Exception:
            self._client = None

    @property
    def backend(self) -> str:
        return "qdrant" if self._client else "memory"

    def ensure_collection(self, dim: int):
        if self._client is None:
            return
        from qdrant_client.models import Distance, VectorParams

        try:
            self._client.get_collection(self.settings.collection)
        except Exception:
            self._client.create_collection(
                collection_name=self.settings.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids: List[str], vectors: List[List[float]], payloads: List[dict]):
        if self._client is not None:
            from qdrant_client.models import PointStruct

            points = [
                PointStruct(id=i, vector=v, payload=p)
                for i, v, p in zip(ids, vectors, payloads)
            ]
            self._client.upsert(collection_name=self.settings.collection, points=points)
        else:
            for i, v, p in zip(ids, vectors, payloads):
                self._memory[i] = (v, p)

    def search(self, vector: List[float], top_k: int) -> List[Tuple[float, dict]]:
        if self._client is not None:
            hits = self._client.search(
                collection_name=self.settings.collection,
                query_vector=vector,
                limit=top_k,
            )
            return [(h.score, h.payload) for h in hits]
        # 内存余弦检索
        scored = [
            (cosine(vector, v), p) for v, p in self._memory.values()
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        if self._client is not None:
            return self._client.count(self.settings.collection).count
        return len(self._memory)
