#!/usr/bin/env bash
# 맥에서 백엔드 실행: 터미널에서  ./backend/run_mac.sh
# 처음 실행 시 가상환경 만들기 → 패키지 설치 → .env 확인 → 서버 시작까지 자동으로 해요.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 가 없어요. https://www.python.org/downloads/macos/ 에서 설치한 뒤 다시 실행하세요."
  exit 1
fi

if [ ! -d .venv ]; then
  echo "▶ 가상환경(.venv) 만드는 중..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "▶ 패키지 설치 확인 중..."
pip install -q --upgrade pip >/dev/null
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "📝 .env 파일을 만들었어요. 텍스트 편집기가 열리면 GH_CLIENT_SECRET= 뒤에 비밀값을 붙여넣고 저장한 다음, 이 스크립트를 다시 실행하세요."
  open -e .env
  exit 1
fi

if ! grep -Eq '^GH_CLIENT_SECRET=[^[:space:]]+' .env; then
  echo "📝 .env 의 GH_CLIENT_SECRET 이 비어 있어요. 텍스트 편집기에서 채우고 저장한 뒤 다시 실행하세요."
  open -e .env
  exit 1
fi

echo "✅ 준비 완료! 브라우저에서 http://localhost:8000/auth/start 로 로그인하세요. (끄려면 Ctrl+C)"
python -m uvicorn app.main:app --reload --port 8000
