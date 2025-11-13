#!/bin/bash

# TrendRadar API 服务器启动脚本 (macOS/Linux)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║ TrendRadar API 服务器启动 (macOS/Linux)  ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "📍 项目目录: ${BLUE}${SCRIPT_DIR}${NC}"
echo ""

# ========================================
# 步骤 1: 检查 Python 环境
# ========================================
echo -e "${BOLD}[1/4] 🔍 检查 Python 环境...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Python3，请先安装 Python 3.10+${NC}"
    echo ""
    echo "安装方法:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS: brew install python@3.10"
    else
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
        echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    fi
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python 版本: ${PYTHON_VERSION}${NC}"
echo ""

# ========================================
# 步骤 2: 检查并安装依赖
# ========================================
echo -e "${BOLD}[2/4] 📦 检查项目依赖...${NC}"

# 检查必要依赖
if ! python3 -c "import uvicorn, fastapi, psutil" &> /dev/null; then
    echo -e "${YELLOW}⚠️  缺少必要依赖，正在安装...${NC}"
    echo ""

    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install -r requirements.txt --quiet

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 依赖安装失败${NC}"
        echo ""
        echo "解决方案:"
        echo "  1. 检查网络连接"
        echo "  2. 手动安装: python3 -m pip install -r requirements.txt"
        echo ""
        exit 1
    fi

    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 依赖已满足${NC}"
fi
echo ""

# ========================================
# 步骤 3: 检查配置文件
# ========================================
echo -e "${BOLD}[3/4] ⚙️  检查配置文件...${NC}"

if [ ! -f "config/config.yaml" ]; then
    echo -e "${YELLOW}⚠️  配置文件不存在，API 服务器将使用默认配置${NC}"
    echo ""
else
    echo -e "${GREEN}✅ 配置文件存在${NC}"
fi
echo ""

# ========================================
# 步骤 4: 启动 API 服务器
# ========================================
echo -e "${BOLD}[4/4] 🚀 启动 API 服务器...${NC}"
echo ""

# 解析命令行参数
HOST="${1:-0.0.0.0}"
PORT="${2:-8000}"

echo -e "监听地址: ${BLUE}${HOST}:${PORT}${NC}"
echo ""
# 首次爬取一下
python3 main.py

# 使用 process_manager.py 启动
python3 scripts/process_manager.py start --service api --host "$HOST" --port "$PORT"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║           启动成功！                      ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    echo "💡 提示:"
    echo "  - API 文档: http://127.0.0.1:${PORT}/docs"
    echo "  - 查看状态: ./status_api.sh"
    echo "  - 停止服务: ./stop_api.sh"
    echo "  - 查看日志: python3 scripts/process_manager.py log --service api"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 启动失败，请检查日志文件${NC}"
    echo ""
fi
