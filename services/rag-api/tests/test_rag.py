"""MorningStar AI — 核心逻辑单测（无重型依赖，可 headless 运行）。

运行：
    python tests/test_rag.py
或：
    pytest tests/test_rag.py
"""
import os
import sys

# 让 app 包可导入（rag-api 为包根）
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from app.rag import chunk_text, reciprocal_rank_fusion, build_prompt  # noqa: E402
from app.embeddings import HashEmbedder  # noqa: E402


def test_chunk_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunk_single_short():
    out = chunk_text("这是一句很短的话。", chunk_size=600, overlap=80)
    assert len(out) == 1
    assert "这是一句很短的话。" in out[0]


def test_chunk_long_splits():
    para = "句子一内容。句子二内容。句子三内容。" * 40
    out = chunk_text(para, chunk_size=120, overlap=20)
    assert len(out) >= 2
    # 不变量：所有 chunk 拼接应覆盖原文主要 token
    joined = " ".join(out)
    assert "句子一内容" in joined
    assert "句子三内容" in joined


def test_chunk_overlap():
    para = ("段落内容重复词 " * 30)
    out = chunk_text(para, chunk_size=80, overlap=10)
    # 多 chunk 时，相邻 chunk 应存在词交叠（tail 保留）
    if len(out) >= 2:
        last_words = set(out[0].split()[-5:])
        first_words = set(out[1].split()[:5])
        assert last_words & first_words


def test_rrf_ordering():
    # A 在两个列表中均排第一 → 融合后第一
    fused = reciprocal_rank_fusion([["A", "B", "C"], ["A", "C", "B"]])
    assert fused[0] == "A"
    assert set(fused) == {"A", "B", "C"}


def test_rrf_dedup():
    fused = reciprocal_rank_fusion([["X", "Y"], ["Y", "X"]])
    assert len(fused) == 2
    assert "X" in fused and "Y" in fused


def test_build_prompt():
    msgs = build_prompt("什么是晨星？", ["晨星是启明星。", "晨星是 AI 助手。"])
    assert msgs[0]["role"] == "system"
    assert "什么是晨星？" in msgs[1]["content"]
    assert "晨星是启明星。" in msgs[1]["content"]


def test_hash_embedder_deterministic():
    e = HashEmbedder(dim=64)
    v1 = e.embed(["晨星 AI 系统"])[0]
    v2 = e.embed(["晨星 AI 系统"])[0]
    assert v1 == v2
    # L2 归一化：模长 ≈ 1
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_hash_embedder_dim():
    e = HashEmbedder(dim=128)
    assert e.dim() == 128
    assert len(e.embed(["x"])[0]) == 128


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  ✅ {t.__name__}")
    print(f"\n全部通过：{passed}/{len(tests)}")


if __name__ == "__main__":
    _run_all()
