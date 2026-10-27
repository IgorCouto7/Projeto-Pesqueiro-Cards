@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute INSTALAR-CAIXA.cmd primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" iniciar.py
pause
