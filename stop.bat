@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title 智学工坊 - 停止服务

echo.
echo ============================================================
echo  智学工坊 - 停止所有服务
echo ============================================================
echo.

echo [i] 停止后端服务（端口 8001）...
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001.*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    set "FOUND=1"
)
if !FOUND! equ 1 ( echo [v] 后端服务已停止 ) else ( echo [i] 未发现后端进程 )

echo [i] 停止前端 Vite（端口 3000）...
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000.*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    set "FOUND=1"
)
if !FOUND! equ 1 ( echo [v] 前端 Vite 已停止 ) else ( echo [i] 未发现前端进程 )

echo.
echo [v] 所有服务已停止
echo.
pause
