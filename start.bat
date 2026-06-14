@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title 智学工坊 - Local Dev

set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8001"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=3000"
set "NO_COLOR=1"
set "FORCE_COLOR=0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "DEBUG=true"

cd /d "%~dp0"
set "PROJECT_DIR=%CD%"

echo.
echo ============================================================
echo  智学工坊 - 本地开发启动脚本
echo ============================================================
echo.
echo [i] 项目目录: %PROJECT_DIR%

echo.
echo [1/5] 检查 uv...
where uv >nul 2>&1
if errorlevel 1 (
    echo [x] uv 未找到，请先安装: https://docs.astral.sh/uv/
    pause
    exit /b 1
)
for /f "delims=" %%v in ('uv --version 2^>nul') do echo     %%v
echo [v] uv 已就绪

echo.
echo [2/5] 检查 Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo [!] Node.js 未找到，将跳过前端
    set "SKIP_FRONTEND=1"
    goto :AFTER_NODE_CHECK
)
for /f "delims=" %%n in ('node --version 2^>nul') do echo     Node.js %%n

where npm >nul 2>&1
if errorlevel 1 (
    echo [!] npm 未找到，将跳过前端
    set "SKIP_FRONTEND=1"
    goto :AFTER_NODE_CHECK
)
for /f "delims=" %%p in ('npm --version 2^>nul') do echo     npm     %%p
echo [v] Node.js 已就绪
:AFTER_NODE_CHECK

if not exist "%PROJECT_DIR%\frontend\package.json" (
    echo [!] frontend\package.json 未找到，将跳过前端
    set "SKIP_FRONTEND=1"
)

echo.
echo [3/5] 安装 Python 依赖...
uv sync
if errorlevel 1 (
    echo [x] uv sync 失败，请检查网络和 pyproject.toml
    pause
    exit /b 1
)
echo [v] Python 依赖已安装

if not defined SKIP_FRONTEND (
    echo.
    echo [4/5] 安装前端依赖...
    cd /d "%PROJECT_DIR%\frontend"
    if not exist "node_modules" (
        call npm install
        if errorlevel 1 (
            echo [!] npm install 失败，将跳过前端
            set "SKIP_FRONTEND=1"
            cd /d "%PROJECT_DIR%"
            goto :AFTER_FRONTEND
        )
    )
    cd /d "%PROJECT_DIR%"
    echo [v] 前端依赖已安装
)
:AFTER_FRONTEND

echo.
echo [i] 释放旧进程占用的端口...
call :KILL_PORT "%BACKEND_PORT%" "backend"
if not defined SKIP_FRONTEND call :KILL_PORT "%FRONTEND_PORT%" "frontend"

echo.
echo [5/5] 启动服务...
echo.
echo ============================================================
echo  后端 API:      http://%BACKEND_HOST%:%BACKEND_PORT%
echo  API 文档:      http://%BACKEND_HOST%:%BACKEND_PORT%/docs
if not defined SKIP_FRONTEND echo  前端页面:      http://%FRONTEND_HOST%:%FRONTEND_PORT%
echo.
echo  按 Ctrl+C 停止前台服务
echo  也可运行 stop.bat 停止所有服务
echo ============================================================
echo.

if not defined SKIP_FRONTEND (
    echo [i] 启动后端 uvicorn（后台）...
    start "智学工坊 backend" /b uv run uvicorn src.main:app --host %BACKEND_HOST% --port %BACKEND_PORT% --reload --no-use-colors

    echo [i] 启动前端 Vite dev server（前台）...
    echo.
    cd /d "%PROJECT_DIR%\frontend"
    call npx vite --host %FRONTEND_HOST% --port %FRONTEND_PORT% --clearScreen false
    cd /d "%PROJECT_DIR%"
) else (
    echo [i] 启动后端 uvicorn（前台）...
    echo.
    uv run uvicorn src.main:app --host %BACKEND_HOST% --port %BACKEND_PORT% --reload --no-use-colors
)

echo.
echo [i] 服务已停止
pause
exit /b 0

:KILL_PORT
set "PORT=%~1"
set "LABEL=%~2"
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr /C:":%PORT%" ^| findstr /C:"LISTENING"') do (
    echo [!] 端口 %PORT% 被进程 %%p 占用，正在停止...
    taskkill /f /pid %%p >nul 2>&1
)
exit /b 0
