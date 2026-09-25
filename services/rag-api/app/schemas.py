"""API 请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class IngestRequest(BaseModel):
    text: str
    source: str = "manual"


class ChatRequest(BaseModel):
    query: str
    stream: bool = False


class SearchResult(BaseModel):
    text: str
    source: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


class HealthResponse(BaseModel):
    status: str
    backend: str
    embed_dim: int
    docs: int
