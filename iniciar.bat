@echo off
rem Windows: clique duas vezes neste arquivo para iniciar.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 iniciar.py
  goto fim
)
where python >nul 2>nul
if %errorlevel%==0 (
  python iniciar.py
  goto fim
)
echo Python 3 nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".
:fim
pause
