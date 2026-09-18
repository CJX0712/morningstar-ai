"""可插拔文本嵌入层。

优先级：
  1. 稠密向量（sentence-transformers，质量最佳，正常网络可用）
  2. 若 HuggingFace 不可达，自动从 ModelScope 下载同款模型（对受限/国内网络友好）
  3. 若仍失败，回退到本地离线哈希向量（保证应用永不崩溃，可降级运行）

所有后端输出统一为「已 L2 归一化」的向量，配合余弦相似度检索。
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import numpy as np

from app.config import BASE_DIR, settings

OFFLINE_DIM = 512
MODELSCOPE_CANDIDATES = [
    "config.json", "modules.json", "model.safetensors", "pytorch_model.bin",
    "vocab.txt", "sentencepiece.bpe.model", "tokenizer.json",
    "tokenizer_config.json", "special_tokens_map.json",
    "1_Pooling/config.json", "README.md",
]


class OfflineEmbedder:
    """纯本地、零依赖的哈希向量器（降级方案）。

    采用词/字 n-gram 哈希 + 词频加权 + L2 归一化，可在任意环境离线运行。
    """

    def __init__(self, dim: int = OFFLINE_DIM) -> None:
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower())
        if not tokens:
            return vec.tolist()
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()


class DenseEmbedder:
    """基于 sentence-transformers 的稠密向量器。"""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = _load_model(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def _load_model(model_name: str):
    """加载稠密向量模型：本地路径 -> ModelScope（首选）-> HuggingFace（兜底）。"""
    from sentence_transformers import SentenceTransformer

    # 1) 本地路径直接加载
    if os.path.isdir(model_name):
        return SentenceTransformer(model_name)
    # 2) 首选 ModelScope（国内 / 受限网络最稳，且全球可达）
    try:
        local = _download_from_modelscope(model_name)
        return SentenceTransformer(local)
    except Exception as e:  # noqa: BLE001
        print(f"[embeddings] ModelScope 加载失败，回退 HuggingFace：{e}")
    # 3) 兜底 HuggingFace
    return SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def _download_from_modelscope(model_id: str) -> str:
    """从 ModelScope 下载模型文件到本地缓存目录，返回本地路径。"""
    import urllib.request

    local = BASE_DIR / "models" / model_id.replace("/", "__")
    local.mkdir(parents=True, exist_ok=True)
    base = f"https://modelscope.cn/models/{model_id}/resolve/master"
    for rel in MODELSCOPE_CANDIDATES:
        dest = local / rel
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{base}/{rel}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "morningstar-ai"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status != 200:
                    continue
                dest.write_bytes(resp.read())
        except Exception:  # noqa: BLE001  该文件不存在则跳过
            continue
    if not (local / "model.safetensors").exists() and not (local / "pytorch_model.bin").exists():
        raise RuntimeError(f"ModelScope 下载失败：{model_id}")
    return str(local)


_EMBEDDER = None


def get_embedder():
    """返回全局嵌入器（懒加载 + 兜底）。"""
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    model = settings.embedding_model
    try:
        _EMBEDDER = DenseEmbedder(model)
        print(f"[embeddings] 使用稠密向量模型：{model} (dim={_EMBEDDER.dim})")
    except Exception as e:  # noqa: BLE001
        print(f"[embeddings] 稠密向量加载失败（{e}），回退本地离线向量。")
        _EMBEDDER = OfflineEmbedder()
    return _EMBEDDER
