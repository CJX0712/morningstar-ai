"""冒烟测试：验证应用可加载、核心端点可用。"""
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_providers():
    with TestClient(app) as c:
        r = c.get("/api/providers")
        assert r.status_code == 200
        data = r.json()
        ids = [p["id"] for p in data["providers"]]
        for needed in ("openai", "deepseek", "zhipu", "qwen", "ollama"):
            assert needed in ids


def test_chat_unconfigured_errors_gracefully():
    """未配置 Key 时，应给出友好错误而非崩溃。"""
    with TestClient(app) as c:
        r = c.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "你好"}], "provider": "openai"},
        )
        assert r.status_code == 200
        body = r.text
        assert "[DONE]" in body
        assert "未配置" in body or "error" in body
