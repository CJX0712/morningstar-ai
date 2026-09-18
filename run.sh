#!/usr/bin/env bash
# 晨星 AI 本地启动脚本（无 Docker 时直接使用）
set -e
PYBIN="$(command -v python3.11 || command -v python3 || echo python3)"
echo "▶ 使用 Python: $PYBIN"
exec "$PYBIN" -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
