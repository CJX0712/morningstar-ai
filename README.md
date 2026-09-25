# MorningStar AI · 端到端 AI 平台

> 作者：晨星（GitHub: CJX0712）
> 本地优先、混合推理、容器化、一键部署的 RAG + Agent 平台。

MorningStar AI 是一套**端到端**的人工智能系统，把"抓取 → 嵌入 → 向量存储 → 检索增强 → 大模型对话 → 前端交互"整合成一条可运行的流水线。设计原则：

- **混合推理**：默认本地量化模型（llama.cpp / GGUF，CPU 可跑 7B-Q4），复杂任务自动降级到云端 OpenAI 兼容端点。
- **本地优先**：数据默认不出本机；云端 API 为可选兜底。
- **容器化**：一份 `docker-compose.yml` 拉起全部服务。
- **零黑盒**：核心检索/分块逻辑有纯 Python 单测护航。

---

## 架构总览

```
┌─────────────┐
│  Web (React) │  对话 / 知识库上传 / 流式响应
└──────┬──────┘
       │ HTTP (REST + SSE)
┌──────▼──────────┐
│   RAG API        │  FastAPI：分块 / 索引 / 混合检索 / 对话
│   (rag-api)      │
└──┬──────────┬────┘
   │          │
┌──▼───┐  ┌───▼─────────┐  ┌──────────────┐
│Qdrant │  │ Embeddings  │  │   LLM        │
│向量库 │  │ 本地/云端    │  │ 本地/云端兜底 │
└──────┘  └─────────────┘  └──────────────┘
   ▲
   │ 抓取
┌──┴──────────┐
│  crawl4ai   │  文档/网页抓取（复用或本仓附）
└─────────────┘
```

详见 [docs/architecture.md](docs/architecture.md)。

## 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| rag-api | 本地构建 | 8000 | RAG 编排 + 对话 API |
| qdrant | qdrant/qdrant | 6333 | 向量数据库 |
| llama-cpp | localai/... 或自建 | 8080 | 本地 GGUF 推理（可选） |
| web | 本地构建 (nginx) | 5173/80 | React 前端 |

## 快速开始

```bash
# 1. 准备环境
cp .env.example .env
# 编辑 .env：设置模型路径 / 云端 API Key（可选）

# 2. 一键启动
docker compose up -d

# 3. 打开前端
open http://localhost:5173
```

详细部署见 [docs/deployment.md](docs/deployment.md)，使用说明见 [docs/usage.md](docs/usage.md)。

## 目录结构

```
morningstar-ai/
├── docker-compose.yml
├── .env.example
├── requirements.lock
├── services/
│   └── rag-api/        # FastAPI 后端
│       ├── app/        # 源码
│       └── tests/      # 单测
├── web/                # React 前端
├── docs/               # 架构/部署/使用文档
└── scripts/            # 辅助脚本
```

## 许可证

MIT © 晨星
