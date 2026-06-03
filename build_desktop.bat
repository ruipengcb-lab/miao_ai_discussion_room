@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 喵酱 AI 讨论室 - 桌面版打包

cd /d "%~dp0"

:: ═══════════════════════════════════════════
::  喵酱 AI 讨论室 - 桌面版一键打包
::  打包后：dist\MiaoAIDiscussionRoom\
::          ├── MiaoAIDiscussionRoom.exe  ← NiceGUI 主程序
::          ├── 启动器.exe                 ← 双击即用（推荐）
::          └── README.md
:: ═══════════════════════════════════════════

:: 激活 venv
call "%~dp0.venv\Scripts\activate.bat"

:: ── 1. 打包 NiceGUI 主程序（onedir，含 Python 运行时）──
echo.
echo [1/2] 正在打包 NiceGUI 主程序（首次可能需要 3-5 分钟）...
if exist "dist\App" rmdir /s /q "dist\App"
if exist "dist\MiaoAIDiscussionRoom" rmdir /s /q "dist\MiaoAIDiscussionRoom"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --name App ^
  --distpath dist ^
  --windowed ^
  --collect-all nicegui ^
  --collect-all fastapi ^
  --collect-all starlette ^
  --collect-all pywebview ^
  --collect-all pythonnet ^
  --collect-all clr_loader ^
  main.py

if errorlevel 1 (
    echo [错误] 打包失败，请检查上方错误信息。
    pause
    exit /b
)
echo [1/2] 完成

:: ── 2. 打包极简启动器（onefile，双击直接运行）──
echo.
echo [2/2] 正在打包启动器...
if exist "dist\LauncherTemp" rmdir /s /q "dist\LauncherTemp"

python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --name 启动器 ^
  --distpath "dist\LauncherTemp" ^
  --windowed ^
  "launcher.py"

if errorlevel 1 (
    echo [警告] 启动器打包失败，主程序仍可正常手动启动。
) else (
    copy /Y "dist\LauncherTemp\启动器.exe" "dist\App\启动器.exe" >nul 2>&1
    echo [2/2] 完成
)

:: ── 3. 整理目录结构 ──
if not exist "dist\MiaoAIDiscussionRoom" (
    move "dist\App" "dist\MiaoAIDiscussionRoom" >nul 2>&1
)
copy /Y "启动桌面版.bat" "dist\MiaoAIDiscussionRoom\启动桌面版.bat" >nul 2>&1
copy /Y "README-桌面版说明.md" "dist\MiaoAIDiscussionRoom\README.md" >nul 2>&1
rmdir /s /q "dist\LauncherTemp" 2>nul

:: 清理 build 目录
rmdir /s /q "build\LauncherTemp" 2>nul

echo.
echo ════════════════════════════════════════════════════════════
echo.
echo   打包完成！
echo.
echo   目录：%~dp0dist\MiaoAIDiscussionRoom\
echo.
echo   使用方法（任选其一）：
echo   1. 双击 [启动器.exe]  → 直接运行（推荐，无黑窗口）
echo   2. 双击 [MiaoAIDiscussionRoom.exe]  → 也可运行
echo   3. 右键 [MiaoAIDiscussionRoom.exe] → 创建桌面快捷方式
echo.
echo   整个文件夹可以完整复制到其他 Windows 电脑直接运行
echo   （无需安装 Python）
echo.
echo ════════════════════════════════════════════════════════════
pause
