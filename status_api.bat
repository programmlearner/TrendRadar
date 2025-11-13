@echo off
chcp 65001 >nul

cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python
    pause
    exit /b 1
)

REM 显示 API 服务器状态
python scripts\process_manager.py status --service api

pause
