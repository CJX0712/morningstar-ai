"""RAG 核心逻辑：分块、混合检索（RRF 融合）、提示词构造、检索编排。

纯函数（chunk_text / reciprocal_rank_fusion / build_prompt）无外部依赖，
可被单测直接调用。RAGService 负责把嵌入 / 向量库 / LLM 串起来。
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

from .config import Settings

SYSTEM_PROMPT = (
    "你是 MorningStar AI 助手，基于用户提供的知识库内容作答。"
    "若知识库没有相关信息，请如实说明，不要编造。"
    "回答使用与用户相同的语言，简洁、结构化。"
)


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> List[str]:
    """按段落优先、再按词切分，保证 chunk 不超过 chunk_size 且相邻重叠 overlap。

    不变量：还原所有 chunk 拼接（去重叠）应包含原文主要信息；
    相邻 chunk 尾部/头部存在 overlap 个词的交叠（当文本足够长时）。
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # 先按句子边界切，避免硬截断
    sentences = re.split(r"(?<=[。！？.!?])", text)
    chunks: List[str] = []
    buf: List[str] = []
    buf_len = 0

    def flush():
        nonlocal buf, buf_len
        if buf:
            chunks.append(" ".join(buf))
            # 重叠：保留最后 overlap 个词作为下一 chunk 开头
            tail = buf[-1].split()
            overlap_words = tail[-overlap:] if overlap > 0 else []
            buf = [" ".join(overlap_words)] if overlap_words else []
            buf_len = len(buf[0]) if buf else 0

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if buf_len + len(s) > chunk_size and buf:
            flush()
        buf.append(s)
        buf_len += len(s) + 1
    flush()
    return chunks


def reciprocal_rank_fusion(rankings: List[List[str]], k: int = 60) -> List[str]:
    """倒数排名融合：把多个有序结果列表融合为单一排序。

    不变量：同一 ranking 内部顺序不变地转化为分数；结果去重。
    """
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda d: scores[d], reverse=True)


def _lexical_score(query: str, text: str) -> float:
    q_tokens = set(re.findall(r"\w+", query.lower()))
    if not q_tokens:
        return 0.0
    t_tokens = re.findall(r"\w+", text.lower())
    if not t_tokens:
        return 0.0
    hits = sum(1 for t in t_tokens if t in q_tokens)
    return hits / math.sqrt(len(t_tokens))


def build_prompt(query: str, contexts: List[str]) -> List[dict]:
    context_block = "\n\n".join(
        f"[文档 {i+1}]\n{c}" for i, c in enumerate(contexts)
    )
    user_msg = f"知识库内容：\n{context_block}\n\n用户问题：{query}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


class RAGService:
    def __init__(
        self,
        settings: Settings,
        embedder=None,
        store=None,
        llm=None,
    ):
        # 重型依赖延迟导入，便于纯逻辑单元在无网络环境单测
        from .embeddings import Embedder  # noqa: F401
        from .llm import FallbackLLM  # noqa: F401
        from .vector_store import VectorStore  # noqa: F401

        self.settings = settings
        self.embedder = embedder
        self.store = store
        self.llm = llm
        self._counter = 0

    def ingest(self, text: str, source: str = "manual") -> int:
        chunks = chunk_text(text, self.settings.chunk_size, self.settings.chunk_overlap)
        if not chunks:
            return 0
        vectors = self.embedder.embed(chunks)
        ids, payloads = [], []
        for c, v in zip(chunks, vectors):
            self._counter += 1
            ids.append(f"doc_{self._counter}")
            payloads.append({"text": c, "source": source})
        self.store.upsert(ids, vectors, payloads)
        return len(chunks)

    def retrieve(self, query: str) -> List[Tuple[float, dict]]:
        vec = self.embedder.embed([query])[0]
        broad = self.store.search(vec, self.settings.top_k * 2)
        if not broad:
            return []
        # 双路排序：稠密(向量) + 词法(lexical)，RRF 融合
        dense_ranking = [p.get("source", "") + str(i) for i, (_, p) in enumerate(broad)]
        # 用 (score, payload) 重新构造稳定 id：以 payload 文本哈希作 id
        id_map = {str(i): p for i, (_, p) in enumerate(broad)}
        dense_ids = list(id_map.keys())
        lexical_ranking = sorted(
            id_map.keys(),
            key=lambda i: _lexical_score(query, id_map[i].get("text", "")),
            reverse=True,
        )
        fused = reciprocal_rank_fusion([dense_ids, lexical_ranking])
        result = []
        for fid in fused[: self.settings.top_k]:
            p = id_map[fid]
            result.append((1.0, p))
        return result

    async def answer(self, query: str, stream: bool = False):
        contexts = [p.get("text", "") for _, p in self.retrieve(query)]
        messages = build_prompt(query, contexts)
        if stream:
            return self.llm.stream(messages)
        return await self.llm.complete(messages)
