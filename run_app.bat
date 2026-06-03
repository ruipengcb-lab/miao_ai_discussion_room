@echo off
chcp 65001 >nul 2>&1
setlocal
cd /d "%~dp0"

if exist "%~dp0..\.venv\Scripts\python.exe" (
    "%~dp0..\.venv\Scripts\python.exe" main.py
    exit /b %errorlevel%
)

python main.py
