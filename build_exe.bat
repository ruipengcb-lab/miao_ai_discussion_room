@echo off
setlocal
cd /d "%~dp0"

set PYTHON=C:\Users\ruipe\AppData\Local\Python\pythoncore-3.14-64\python.exe

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
