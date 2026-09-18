"""RAG 检索增强：文档摄取与向量检索。

流程：上传文档 -> 分块 -> 嵌入（可插拔：稠密/ModelScope/离线）-> Chroma 持久化；
查询时：嵌入问题 -> 向量检索 Top-K 片段 -> 作为上下文注入智能体。
无需外部向量服务，全部本地持久化。
"""
from __future__ import annotations

import re
from pathlib import Path

import chromadb

from app.config import settings
from app.embeddings import get_embedder


class RAG:
    def __init__(self) -> None:
        self._embedder = None
        self._client: chromadb.PersistentClient | None = None
        self._collection: chromadb.Collection | None = None

    # ---------- 懒加载 ----------
    def _ensure(self) -> None:
        if self._embedder is None:
            self._embedder = get_embedder()
        if self._client is None:
            Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
            Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            name = settings.collection_name
            dim = self._embedder.dim
            # 若已有集合的向量维度与当前嵌入器不一致，则重建（避免维度不匹配崩溃）
            existing = None
            try:
                existing = self._client.get_collection(name)
                if (existing.metadata or {}).get("dim") != dim:
                    self._client.delete_collection(name)
                    existing = None
            except Exception:  # noqa: BLE001
                existing = None
            if existing is None:
                self._collection = self._client.create_collection(
                    name, metadata={"dim": dim, "hnsw:space": "cosine"}
                )
            else:
                self._collection = existing

    def _embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure()
        return self._embedder.encode(texts)

    # ---------- 分块 ----------
    @staticmethod
    def _chunk(text: str, size: int, overlap: int) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= size:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
        return chunks

    # ---------- 摄取 ----------
    def ingest_text(self, text: str, source: str) -> int:
        pieces = self._chunk(text, settings.chunk_size, settings.chunk_overlap)
        if not pieces:
            return 0
        embeddings = self._embed(pieces)
        ids = [f"{source}::{i}" for i in range(len(pieces))]
        metadatas = [{"source": source, "chunk": i} for i in range(len(pieces))]
        self._collection.add(
            documents=pieces, embeddings=embeddings, ids=ids, metadatas=metadatas
        )
        return len(pieces)

    def ingest_file(self, path: str | Path) -> int:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = self._read_pdf(path)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
        return self.ingest_text(text, source=path.name)

    @staticmethod
    def _read_pdf(path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    # ---------- 检索 ----------
    def query(self, question: str, k: int | None = None) -> list[dict]:
        k = k or settings.top_k
        qvec = self._embed([question])[0]
        res = self._collection.query(query_embeddings=[qvec], n_results=k)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        out: list[dict] = []
        for doc, meta in zip(docs, metas):
            out.append({"content": doc, "source": (meta or {}).get("source", "未知")})
        return out

    def list_documents(self) -> list[dict]:
        data = self._collection.get(include=["metadatas"])
        meta_list = data.get("metadatas", []) or []
        counts: dict[str, int] = {}
        for m in meta_list:
            src = (m or {}).get("source", "未知")
            counts[src] = counts.get(src, 0) + 1
        return [{"source": s, "chunks": c} for s, c in counts.items()]

    def clear(self) -> int:
        data = self._collection.get(include=[])
        ids = data.get("ids", []) or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    @property
    def ready(self) -> bool:
        try:
            self._ensure()
            return True
        except Exception:  # noqa: BLE001
            return False


# 全局单例
rag = RAG()
