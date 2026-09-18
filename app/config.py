"""全局配置：通过环境变量 / .env 文件加载。

每个大模型提供方只需填写对应 API Key 即可启用；本地 Ollama 无需 Key。
"""
from __future__ import annotations

import os

# HuggingFace 端点兜底：在受限网络（如国内）自动改用镜像，
# 保证 sentence-transformers 嵌入模型可正常下载。可用环境变量覆盖。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# 关闭 Chroma 匿名遥测，保持日志干净
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（此文件位于 app/ 下）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 服务 ----
    app_name: str = "MorningStar AI"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ---- 大模型提供方（按需填写 Key）----
    default_provider: str = "openai"
    # OpenAI 兼容协议的各厂默认模型
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    zhipu_api_key: str = ""          # 智谱 GLM
    zhipu_model: str = "glm-4-flash"

    qwen_api_key: str = ""           # 通义千问
    qwen_model: str = "qwen-plus"

    # 本地 Ollama（无需 Key，需本机运行 `ollama serve`）
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b"

    # ---- 嵌入与向量库（RAG）----
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_persist_dir: str = str(BASE_DIR / "data" / "vectorstore")
    uploads_dir: str = str(BASE_DIR / "data" / "uploads")
    collection_name: str = "morningstar_docs"

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4

    # ---- 智能体 ----
    max_tool_rounds: int = 6
    temperature: float = 0.7

    # ---- 联网搜索（可选；留空则使用 DuckDuckGo HTML 抓取）----
    serpapi_key: str = ""

    @property
    def providers(self) -> dict[str, dict]:
        return {
            "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1",
                       "api_key": self.openai_api_key, "default_model": self.openai_model},
            "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
                         "api_key": self.deepseek_api_key, "default_model": self.deepseek_model},
            "zhipu": {"label": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4",
                      "api_key": self.zhipu_api_key, "default_model": self.zhipu_model},
            "qwen": {"label": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                     "api_key": self.qwen_api_key, "default_model": self.qwen_model},
            "ollama": {"label": "本地 Ollama", "base_url": self.ollama_base_url,
                       "api_key": "ollama", "default_model": self.ollama_model},
        }


settings = Settings()
