@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
  echo 먼저 setup.bat 을 더블클릭해서 설치를 끝내세요.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python main.py %*
pause
