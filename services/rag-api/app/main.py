"""MorningStar AI — RAG API 主入口。

端点：
  GET  /health   健康检查
  POST /ingest   写入文本（构建知识库）
  POST /search   检索相关片段
  POST /chat     对话（支持 SSE 流式）
"""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import settings
from .embeddings import build_embedder
from .llm import build_llm
from .rag import RAGService
from .schemas import (
    ChatRequest,
    HealthResponse,
    IngestRequest,
    SearchResponse,
    SearchResult,
)
from .vector_store import VectorStore

app = FastAPI(title="MorningStar AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时装配（单例）
embedder = build_embedder(settings)
store = VectorStore(settings)
store.ensure_collection(embedder.dim())
llm = build_llm(settings)
rag = RAGService(settings, embedder, store, llm)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        backend=store.backend,
        embed_dim=embedder.dim(),
        docs=store.count(),
    )


@app.post("/ingest")
def ingest(req: IngestRequest):
    n = rag.ingest(req.text, req.source)
    return {"ingested_chunks": n, "total_docs": store.count()}


@app.post("/search", response_model=SearchResponse)
def search(req: ChatRequest):
    hits = rag.retrieve(req.query)
    return SearchResponse(
        results=[SearchResult(text=p.get("text", ""), source=p.get("source", "")) for _, p in hits]
    )


@app.post("/chat")
async def chat(req: ChatRequest):
    if req.stream:
        async def event_gen():
            async for tok in await rag.answer(req.query, stream=True):
                yield f"data: {json.dumps({'token': tok}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    answer = await rag.answer(req.query, stream=False)
    return {"answer": answer, "backend": store.backend}
