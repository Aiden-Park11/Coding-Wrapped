"""환경변수 설정. 비밀값은 .env 에만 두고 절대 커밋하지 않는다."""
import os

from dotenv import load_dotenv

load_dotenv()

# GitHub App (Settings → Developer settings → GitHub Apps 에서 발급)
APP_SLUG = os.getenv("GH_APP_SLUG", "")            # 예: knu-code-wrapped
CLIENT_ID = os.getenv("GH_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GH_CLIENT_SECRET", "")

# solved.ac 공식 API v4 앱 키 (solved.ac Backstage 에서 발급, 모든 요청에 필요)
SOLVEDAC_CLIENT_ID = os.getenv("SOLVEDAC_CLIENT_ID", "")
SOLVEDAC_CLIENT_SECRET = os.getenv("SOLVEDAC_CLIENT_SECRET", "")

# 이 서버의 공개 주소 (콜백 URL = BASE_URL + /auth/callback)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

# 분석 기간: WRAPPED_YEAR 년 1월 1일부터
WRAPPED_YEAR = int(os.getenv("WRAPPED_YEAR", "2026"))

# 속도 제한 장치
MAX_COMMITS_PER_REPO = int(os.getenv("MAX_COMMITS_PER_REPO", "1000"))
MAX_DETAIL_COMMITS = int(os.getenv("MAX_DETAIL_COMMITS", "60"))   # 파일·줄 수 조회할 최근 커밋 수
CONCURRENCY = int(os.getenv("GH_CONCURRENCY", "8"))

COOKIE_SECURE = BASE_URL.startswith("https://")
SESSION_TTL_SEC = 2 * 60 * 60


def github_ready() -> bool:
    return bool(APP_SLUG and CLIENT_ID and CLIENT_SECRET)
