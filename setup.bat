@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] 가상환경(.venv) 만드는 중...
python -m venv .venv
if errorlevel 1 (
  echo 파이썬을 찾을 수 없습니다. README.md 의 "1. 파이썬 설치" 를 먼저 하세요.
  pause
  exit /b 1
)

echo [2/2] 필요한 라이브러리 설치 중... (몇 분 걸릴 수 있습니다)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo 설치에 실패했습니다. 위의 빨간 오류 메시지를 확인하세요.
  pause
  exit /b 1
)

echo.
echo 설치 완료! 이제 run.bat 을 더블클릭하세요.
pause
