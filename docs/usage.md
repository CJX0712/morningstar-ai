# 使用手册 · MorningStar AI

> 作者：晨星

## 1. 建库（入库知识）

两种方式：

**A. 网页端**：左侧粘贴文本或选择 `.txt/.md/.json` 文件 → 点「入库」。
**B. API**：

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text":"晨星是启明星，是在别人还没醒时把活干完的守夜者。","source":"demo"}'
```

返回：`{"ingested_chunks":N,"total_docs":M}`

## 2. 提问（对话）

**网页端**：底部输入框输入问题，回车或点「发送」，答案流式出现。
**API（流式）**：

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"晨星是什么？","stream":true}'
```

SSE 输出：`data: {"token":"晨"}` … `data: [DONE]`

**非流式**：`{"query":"...","stream":false}` → `{"answer":"...","backend":"memory"}`

## 3. 检索（只看相关片段）

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"晨星是什么？"}'
```

返回 top-K 片段及其来源。

## 4. 健康检查

```bash
curl http://localhost:8000/health
# {"status":"ok","backend":"qdrant","embed_dim":512,"docs":42}
```

## 5. 切换推理后端

| 场景 | 配置 |
|------|------|
| 纯本地（默认） | `LLM_PROVIDER=local` |
| 本地 + 云端兜底 | 同时填 `CLOUD_LLM_*`；本地超时自动降级 |
| 仅云端 | `LLM_PROVIDER=local` 但 `LLM_BASE_URL` 指向云端 |

## 6. 常见问题

- **首次很慢**：本地嵌入模型需联网下载一次权重（之后缓存）。
- **内存模式**：Qdrant 未启动时会自动用内存存储，重启数据清空；生产务必起 Qdrant。
- **中文效果差**：默认 `bge-small-zh` 已针对中文优化；可换更大模型提升召回。
