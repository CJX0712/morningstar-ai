"""MorningStar AI — FastAPI 主程序。

提供：
  - Web 前端托管（聊天界面）
  - /api/chat        SSE 流式对话（多后端 + 智能体 + RAG）
  - /api/providers   可用模型提供方与配置状态
  - /api/upload      文档上传并摄取进知识库
  - /api/documents   已索引文档列表
  - /api/clear_rag   清空知识库
  - /api/health      健康检查
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.agent import Agent
from app.config import BASE_DIR, settings
from app.rag import rag
from app.schemas import ChatRequest, DocumentInfo, UploadResponse

FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/providers")
async def providers():
    out = []
    for pid, cfg in settings.providers.items():
        configured = (pid == "ollama") or bool(cfg["api_key"])
        out.append(
            {
                "id": pid,
                "label": cfg["label"],
                "default_model": cfg["default_model"],
                "configured": configured,
            }
        )
    return {"providers": out, "default_provider": settings.default_provider}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    agent = Agent(
        provider=req.provider,
        model=req.model,
        use_rag=req.use_rag,
        temperature=req.temperature,
    )

    # 前置校验：提供方是否可用
    if not agent.llm.is_configured():
        async def err():
            yield _sse({"type": "error", "message": f"提供方「{req.provider}」未配置 API Key，请在 .env 中填写。"})
            yield "data: [DONE]\n\n"

        return StreamingResponse(err(), media_type="text/event-stream")

    async def event_stream():
        try:
            async for ev in agent.run(req.messages):
                yield _sse(ev)
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "message": f"对话出错: {exc}"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    dest = Path(settings.uploads_dir) / file.filename
    content = await file.read()
    dest.write_bytes(content)
    try:
        chunks = await asyncio.to_thread(rag.ingest_file, dest)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"摄取失败: {exc}")
    return UploadResponse(filename=file.filename, chunks=chunks, status="indexed")


@app.get("/api/documents", response_model=list[DocumentInfo])
async def documents():
    try:
        data = await asyncio.to_thread(rag.list_documents)
    except Exception:  # noqa: BLE001
        return []
    return [DocumentInfo(id=d["source"], source=d["source"], chunks=d["chunks"]) for d in data]


@app.post("/api/clear_rag")
async def clear_rag():
    try:
        n = await asyncio.to_thread(rag.clear)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"清空失败: {exc}")
    return {"cleared": n}


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
