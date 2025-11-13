@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ╔═══════════════════════════════════════════╗
echo ║   TrendRadar API 服务器启动 (Windows)    ║
echo ╚═══════════════════════════════════════════╝
echo.

REM 获取脚本所在目录
cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"

echo 📍 项目目录: %PROJECT_ROOT%
echo.

REM ========================================
REM 步骤 1: 检查 Python 环境
REM ========================================
echo [1/4] 🔍 检查 Python 环境...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python，请先安装 Python 3.10+
    echo.
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python 版本: %PYTHON_VERSION%
echo.

REM ========================================
REM 步骤 2: 检查并安装依赖
REM ========================================
echo [2/4] 📦 检查项目依赖...

REM 检查必要依赖
python -c "import uvicorn, fastapi, psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  缺少必要依赖，正在安装...
    echo.

    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt --quiet

    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        echo.
        echo 解决方案:
        echo   1. 检查网络连接
        echo   2. 手动安装: python -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )

    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已满足
)
echo.

REM ========================================
REM 步骤 3: 检查配置文件
REM ========================================
echo [3/4] ⚙️  检查配置文件...

if not exist "config\config.yaml" (
    echo ⚠️  配置文件不存在，API 服务器将使用默认配置
    echo.
) else (
    echo ✅ 配置文件存在
)
echo.

REM ========================================
REM 步骤 4: 启动 API 服务器
REM ========================================
echo [4/4] 🚀 启动 API 服务器...
echo.

REM 解析命令行参数
set "HOST=0.0.0.0"
set "PORT=8000"

if not "%1"=="" set "HOST=%1"
if not "%2"=="" set "PORT=%2"

echo 监听地址: %HOST%:%PORT%
echo.

REM 使用 process_manager.py 启动
python scripts\process_manager.py start --service api --host %HOST% --port %PORT%

if %errorlevel% equ 0 (
    echo.
    echo ╔═══════════════════════════════════════════╗
    echo ║           启动成功！                      ║
    echo ╚═══════════════════════════════════════════╝
    echo.
    echo 💡 提示:
    echo   - API 文档: http://%HOST%:%PORT%/docs
    echo   - 查看状态: status_api.bat
    echo   - 停止服务: stop_api.bat
    echo   - 查看日志: python scripts\process_manager.py log --service api
    echo.
) else (
    echo.
    echo ❌ 启动失败，请检查日志文件
    echo.
)

pause
