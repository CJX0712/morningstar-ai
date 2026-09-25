"""MorningStar AI — 运行时配置。

集中读取环境变量，提供带默认值的配置对象。
所有配置均可被 .env 或容器 environment 覆盖。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # 向量库
    qdrant_url: str = "http://qdrant:6333"
    collection: str = "morningstar"

    # 嵌入
    embed_provider: str = "local"   # local | cloud
    embed_model: str = "BAAI/bge-small-zh-v1.5"
    embed_dim: int = 512

    # 本地 LLM（llama.cpp / OpenAI 兼容）
    llm_provider: str = "local"     # local | cloud
    llm_base_url: str = "http://llama-cpp:8080/v1"
    llm_model: str = "local"

    # 云端兜底 LLM
    cloud_llm_base_url: str = ""
    cloud_llm_api_key: str = ""
    cloud_llm_model: str = ""

    # 检索参数
    top_k: int = 6
    chunk_size: int = 600
    chunk_overlap: int = 80

    @classmethod
    def from_env(cls) -> "Settings":
        def env(key: str, default: str) -> str:
            return os.getenv(key, default)

        return cls(
            qdrant_url=env("QDRANT_URL", cls.qdrant_url),
            collection=env("COLLECTION", cls.collection),
            embed_provider=env("EMBED_PROVIDER", cls.embed_provider),
            embed_model=env("EMBED_MODEL", cls.embed_model),
            llm_provider=env("LLM_PROVIDER", cls.llm_provider),
            llm_base_url=env("LLM_BASE_URL", cls.llm_base_url),
            llm_model=env("LLM_MODEL", cls.llm_model),
            cloud_llm_base_url=env("CLOUD_LLM_BASE_URL", cls.cloud_llm_base_url),
            cloud_llm_api_key=env("CLOUD_LLM_API_KEY", cls.cloud_llm_api_key),
            cloud_llm_model=env("CLOUD_LLM_MODEL", cls.cloud_llm_model),
            top_k=int(env("TOP_K", str(cls.top_k))),
            chunk_size=int(env("CHUNK_SIZE", str(cls.chunk_size))),
            chunk_overlap=int(env("CHUNK_OVERLAP", str(cls.chunk_overlap))),
        )


settings = Settings.from_env()
