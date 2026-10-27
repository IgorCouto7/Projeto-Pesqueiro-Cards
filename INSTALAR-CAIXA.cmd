@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 (
  echo Instale Python 3.12 ou superior e tente novamente.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Falha ao instalar. Confira sua conexao com a internet.
  pause
  exit /b 1
)
echo Instalacao concluida. Abra INICIAR-CAIXA.cmd.
pause
