@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 喵酱 AI 讨论室 - 前后端一体化打包

cd /d "%~dp0"

echo.
echo ════════════════════════════════════════════════════════════
echo   喵酱 AI 讨论室 - 前后端一体化打包
echo   输出：frontend\release\ 下的便携版 exe
echo ════════════════════════════════════════════════════════════
echo.

:: ── 0. 检查 Python ──
set "PYTHON=C:\Users\ruipe\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PYTHON%" (
    echo [错误] 找不到 Python: %PYTHON%
    pause
    exit /b 1
)

:: ── 1. 构建 React 前端 ──
echo [1/3] 构建 React 前端...
cd /d "%~dp0frontend"
call npm run build 2>&1
if errorlevel 1 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)
echo [1/3] 完成

:: ── 2. 打包 Python 后端（onedir） ──
echo.
echo [2/3] 打包 Python 后端...
cd /d "%~dp0"
"%PYTHON%" -m PyInstaller --noconfirm --clean miao-backend.spec 2>&1
if errorlevel 1 (
    echo [错误] 后端打包失败
    pause
    exit /b 1
)
echo [2/3] 完成

:: ── 3. 打包 Electron 桌面应用（整合前端+后端） ──
echo.
echo [3/3] 打包 Electron 桌面应用...
cd /d "%~dp0frontend"
call npx electron-builder --win portable 2>&1
if errorlevel 1 (
    echo [错误] Electron 打包失败
    pause
    exit /b 1
)
echo [3/3] 完成

echo.
echo ════════════════════════════════════════════════════════════
echo.
echo   打包完成！
echo.
echo   输出目录：%~dp0frontend\release\
echo.
echo   便携版 exe 可直接双击运行，无需安装 Python 或 Node.js
echo   可复制到其他 Windows 电脑直接使用
echo.
echo ════════════════════════════════════════════════════════════
pause
