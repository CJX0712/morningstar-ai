# 部署手册 · MorningStar AI

> 作者：晨星

## 前置条件

- Docker + Docker Compose（Linux / macOS / Windows WSL2）
- 本地推理：准备一个 GGUF 模型放到 `./models/`（如 `qwen2.5-7b-instruct-q4_k_m.gguf`）
- 云端兜底（可选）：一个 OpenAI 兼容端点的 URL + API Key

## 方式一：全容器（推荐）

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env，设置模型名 / 云端密钥（可选）

# 2. 准备模型（本地推理需要）
mkdir -p models
# 把你的 .gguf 放到 models/ 并保持 LLM_MODEL_NAME 一致

# 3. 启动（含本地 LLM）
docker compose --profile local-llm up -d build

# 4. 查看
docker compose ps
curl http://localhost:8000/health
```

前端访问：http://localhost:5173

## 方式二：仅后端（开发）

```bash
cd services/rag-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 无 GPU / 无模型时，Embedder 自动降级为确定性 `HashEmbedder`，
> 后端用内存向量库，整套逻辑仍可在笔记本上跑通（适合先验证 pipeline）。

## 方式三：前端独立开发

```bash
cd web
npm install
npm run dev        # http://localhost:5173，/api 自动反代到 :8000
```

## 端口映射

| 服务 | 容器内 | 宿主机 | 说明 |
|------|--------|--------|------|
| rag-api | 8000 | 8000 | REST / SSE |
| qdrant | 6333 | 6333 | 向量库 |
| llama-cpp | 8080 | 8080 | 本地推理 |
| web | 80 | 5173 | 前端 |

## 公网暴露（可选）

已有 FRP 链路时，把 `8000`/`5173` 经云服反代即可。注意：
- 前端走 HTTPS，避免混合内容拦截；
- 云端密钥只放服务端 `.env`，**绝不**进前端或仓库。
