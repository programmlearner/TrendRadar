#!/bin/bash

# TrendRadar API 服务器停止脚本 (macOS/Linux)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║ TrendRadar API 服务器停止 (macOS/Linux)  ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Python${NC}"
    echo ""
    exit 1
fi

echo "🛑 正在停止 API 服务器..."

# 解析强制停止参数
if [ "$1" == "--force" ] || [ "$1" == "-f" ]; then
    python3 scripts/process_manager.py stop --service api --force
else
    python3 scripts/process_manager.py stop --service api
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 停止成功${NC}"
else
    echo ""
    echo -e "${RED}❌ 停止失败${NC}"
fi

echo ""
