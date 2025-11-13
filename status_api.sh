#!/bin/bash

# TrendRadar API 服务器状态查看脚本 (macOS/Linux)

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到 Python"
    exit 1
fi

# 显示 API 服务器状态
python3 scripts/process_manager.py status --service api
