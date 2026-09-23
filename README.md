<div align="center">

# ✦ 晨星 AI · MorningStar

<p align="center">
  <a href="https://github.com/CJX0712/morningstar-ai/actions/workflows/ci.yml"><img src="https://github.com/CJX0712/morningstar-ai/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <a href="https://github.com/CJX0712/morningstar-ai/releases"><img src="https://img.shields.io/github/v/release/CJX0712/morningstar-ai?sort=semver" alt="release"></a>
  <a href="https://github.com/CJX0712/morningstar-ai/blob/main/LICENSE"><img src="https://img.shields.io/github/license/CJX0712/morningstar-ai" alt="license"></a>
  <img src="https://img.shields.io/badge/author-%E6%99%A8%E6%98%9F-1f6feb" alt="author">
</p>

**世界级 AI 智能体应用 · 复用全网顶尖创新成果**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com)

一个开箱即用的 AI 智能体：多模型切换 · 联网搜索 · 代码执行 · 检索增强（RAG）· 流式对话。

</div>

---

## ✨ 特性

- **🌐 多后端大模型适配**：一套代码切换 OpenAI / DeepSeek / 智谱 GLM / 通义千问（云端 API）与本地 **Ollama**，无需改动业务代码。
- **🤖 ReAct 智能体编排**：内置工具调用循环，模型可自主决定搜索、计算、执行代码。
- **🛠️ 内置工具集**：`web_search`（联网搜索）、`calculate`（安全计算）、`run_python`（沙箱代码执行），工具注册表化、易扩展。
- **📚 检索增强（RAG）**：上传 `txt / md / pdf` 文档，自动分块 → 向量嵌入 → 持久化检索，对话时注入上下文。
  - 嵌入模型**三级自动降级**：本地缓存 → ModelScope 下载（对国内/受限网络友好）→ 离线哈希向量，保证服务永不硬崩。
- **⚡ 流式对话**：基于 SSE 的逐字流式输出，前端实时渲染，原生 Markdown 支持（离线可用）。
- **🐳 一键部署**：提供 `Dockerfile` 与 `docker-compose.yml`，容器化运行。

## 🏗️ 架构

```
┌─────────────┐     ┌─────────────────────────── FastAPI ───────────────────────────┐
│  浏览器前端   │────▶│  /api/chat (SSE) ─▶ Agent(ReAct 循环)                          │
│ (原生 HTML/JS)│◀────│                        │  ├─ LLM 多后端适配 (openai SDK)         │
│  聊天界面     │     │  /api/upload ─▶ RAG 摄取 │  ├─ 工具调用 (search/calc/code)        │
└─────────────┘     │  /api/documents         │  └─ 知识库检索 (向量)                    │
                    │  /api/providers         └───────────────────────────────────────┘
                    └─────────────────────────────────────────────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                     sentence-transformers    Chroma 向量库（持久化）
```

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + Uvicorn + SSE |
| 大模型接入 | OpenAI SDK（兼容协议） |
| 嵌入模型 | `sentence-transformers/all-MiniLM-L6-v2` |
| 向量存储 | Chroma（本地持久化） |
| 前端 | 原生 HTML / CSS / JavaScript |
| 部署 | Docker / docker-compose |

## 🚀 快速开始

### 方式一：本地运行（推荐开发）

```bash
# 1. 安装依赖（Python 3.11）
pip install -r requirements.txt

# 2. 配置模型 Key
cp .env.example .env
# 编辑 .env，填入你要用的提供方 API Key（例如 OPENAI_API_KEY）

# 3. 启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 或： bash run.sh
```

打开浏览器访问 **http://localhost:8000** 即可对话。

### 方式二：Docker

```bash
cp .env.example .env   # 填入 Key
docker compose up -d --build
# 访问 http://localhost:8000
```

### 使用本地 Ollama（免 Key）

```bash
ollama serve
ollama pull qwen2.5:7b
```

在 `.env` 中设置 `OLLAMA_MODEL=qwen2.5:7b`，前端选择「本地 Ollama」即可。

## ⚙️ 配置

在 `.env` 中按需填写（只填要用的提供方）：

| 变量 | 说明 | 默认 |
|---|---|---|
| `DEFAULT_PROVIDER` | 默认提供方 | `openai` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI | `gpt-4o-mini` |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | DeepSeek | `deepseek-chat` |
| `ZHIPU_API_KEY` / `ZHIPU_MODEL` | 智谱 GLM | `glm-4-flash` |
| `QWEN_API_KEY` / `QWEN_MODEL` | 通义千问 | `qwen-plus` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 本地 Ollama | `qwen2.5:7b` |
| `SERPAPI_KEY` | 增强联网搜索（可选） | 空 → 用 DuckDuckGo |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `TOP_K` | RAG 参数 | 800 / 120 / 4 |
| `EMBEDDING_MODEL` | 嵌入模型（可填本地路径） | `all-MiniLM-L6-v2` |
| `HF_ENDPOINT` | HuggingFace 镜像端点 | 自动设为 `hf-mirror.com` |

> **网络受限环境提示**：嵌入模型会优先从 **ModelScope** 下载并缓存到 `models/`，无需翻墙。
> 若全部下载源均不可达，会自动退化为本地离线向量，RAG 仍可运行（召回质量略降）。

## 🔌 API 速览

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/providers` | 可用模型提供方与配置状态 |
| `POST` | `/api/chat` | 流式对话（SSE），body 见 `app/schemas.py` |
| `POST` | `/api/upload` | 上传文档到知识库（form-data `file`） |
| `GET` | `/api/documents` | 已索引文档列表 |
| `POST` | `/api/clear_rag` | 清空知识库 |

**`/api/chat` 请求示例：**

```json
{
  "messages": [{"role": "user", "content": "用代码算 1 到 100 的和"}],
  "provider": "openai",
  "model": "gpt-4o-mini",
  "use_rag": false,
  "temperature": 0.7
}
```

响应为 SSE 事件流：`{"type":"token","text":"…"}`、`{"type":"tool","name":…}`、`{"type":"done"}`。

## 🧩 扩展工具

在 `app/tools/__init__.py` 的注册表中新增一项即可，智能体会自动获得调用能力：

```python
{
    "name": "get_weather",
    "func": get_weather,
    "description": "查询城市天气",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}
```

## 🧪 测试

```bash
python -m pytest tests/ -q
```

## 🗺️ 路线图

- [ ] 多智能体协作（Planner / Executor）
- [ ] 对话历史持久化（SQLite / Redis）
- [ ] 语音输入输出
- [ ] 插件市场与 MCP 协议支持

## 📄 许可证

[MIT](LICENSE) — 作者 **晨星 (MorningStar)**。

> 本项目站在开源巨人的肩膀上：FastAPI、OpenAI SDK、sentence-transformers、Chroma、PyPDF 等。
