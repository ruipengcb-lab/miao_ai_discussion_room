@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 喵酱 AI 讨论室 - 前后端一体化打包

cd /d "%~dp0"

echo.
echo ============================================================
echo   喵酱 AI 讨论室 - 前后端一体化打包
echo   输出：frontend\release\ 下的便携版 exe
echo ============================================================
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON=%~dp0.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 Python。请先安装 Python，或在项目目录创建 .venv。
    pause
    exit /b 1
)

echo [1/3] 构建 React 前端...
cd /d "%~dp0frontend"
call npm install
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)
echo [1/3] 完成

echo.
echo [2/3] 打包 Python 后端...
cd /d "%~dp0"
"%PYTHON%" -m PyInstaller --noconfirm --clean miao-backend.spec
if errorlevel 1 (
    echo [错误] 后端打包失败
    pause
    exit /b 1
)
echo [2/3] 完成

echo.
echo [3/3] 打包 Electron 桌面应用...
cd /d "%~dp0frontend"
call npx electron-builder --win portable
if errorlevel 1 (
    echo [错误] Electron 打包失败
    pause
    exit /b 1
)
echo [3/3] 完成

echo.
echo ============================================================
echo   打包完成！
echo   输出目录：%~dp0frontend\release\
echo   便携版 exe 可直接双击运行，无需安装 Python 或 Node.js
echo ============================================================
pause
