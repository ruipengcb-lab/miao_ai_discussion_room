@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON=%~dp0.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

"%PYTHON%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --name MiaoAIDiscussionRoom ^
  --collect-all nicegui ^
  --collect-all fastapi ^
  --collect-all starlette ^
  main.py

echo.
echo Build finished: %~dp0dist\MiaoAIDiscussionRoom\MiaoAIDiscussionRoom.exe
pause
