@echo off
chcp 65001 >nul

cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python
    pause
    exit /b 1
)

echo 🛑 正在停止 API 服务器...

REM 解析强制停止参数
if /i "%1"=="--force" (
    python scripts\process_manager.py stop --service api --force
) else (
    python scripts\process_manager.py stop --service api
)

if %errorlevel% equ 0 (
    echo.
    echo ✅ 停止成功
) else (
    echo.
    echo ❌ 停止失败
)

echo.
pause
