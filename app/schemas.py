"""请求 / 响应数据模型。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    # OpenAI 工具调用消息字段（可选）
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = Field(default="openai")
    model: Optional[str] = None
    use_rag: bool = False
    temperature: float = 0.7


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    status: str


class DocumentInfo(BaseModel):
    id: str
    source: str
    chunks: int
