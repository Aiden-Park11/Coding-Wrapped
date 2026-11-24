"""코딩 Wrapped 백엔드 (FastAPI)

흐름: /auth/start → GitHub 설치·승인 → /auth/callback → 백그라운드 분석 → /api/wrapped 로 결과 조회
프론트(prototype/)도 이 서버가 같이 서빙해서 쿠키·CORS 문제를 없앤다.
"""
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .boj import HANDLE_RE, fetch_boj
from .github import GitHub, GitHubError, collect_all, exchange_code, get_installations, get_user
from .stats import compute

client = httpx.AsyncClient(timeout=20)
log = logging.getLogger("coding_wrapped")


@asynccontextmanager
async def lifespan(_app):
    yield
    await client.aclose()


app = FastAPI(title="Coding Wrapped", lifespan=lifespan)

# 해커톤 규모라 메모리에 보관. 토큰은 저장하지 않고 분석 결과만 남긴다.
SESSIONS: dict[str, dict] = {}
SID_COOKIE, STATE_COOKIE, RETURNING_COOKIE = "cw_sid", "cw_state", "cw_returning"
_TASKS: set[asyncio.Task] = set()   # 백그라운드 작업이 GC 로 사라지지 않게 참조 보관


def _cookie_args(max_age: int) -> dict:
    return {"httponly": True, "secure": config.COOKIE_SECURE, "samesite": "lax", "max_age": max_age}


def _cleanup() -> None:
    now = time.time()
    for sid in [s for s, v in SESSIONS.items() if now - v["created"] > config.SESSION_TTL_SEC]:
        SESSIONS.pop(sid, None)


@app.get("/health")
async def health():
    """무료 호스팅 잠자기 방지용 핑 주소"""
    return {"ok": True, "github_configured": config.github_ready()}


# ---------- 로그인 ----------

@app.get("/auth/start")
async def auth_start(request: Request):
    if not config.github_ready():
        raise HTTPException(503, "GitHub App 환경변수가 설정되지 않았어요 (.env 확인)")
    state = secrets.token_urlsafe(24)
    if request.cookies.get(RETURNING_COOKIE) or request.query_params.get("login") == "1":
        # 이미 설치한 사용자(이 브라우저에서 로그인한 적 있거나 '바로 로그인'을 누른 경우):
        # 설치 화면 없이 바로 승인 (이미 승인했다면 클릭 없이 통과)
        # 설치 화면으로 보내면 GitHub가 설치 설정 페이지만 보여 주고 돌아오지 않음
        url = "https://github.com/login/oauth/authorize?" + urlencode({
            "client_id": config.CLIENT_ID,
            "redirect_uri": f"{config.BASE_URL}/auth/callback",
            "state": state,
        })
    else:
        url = _install_url(state)
    resp = RedirectResponse(url)
    resp.set_cookie(STATE_COOKIE, state, **_cookie_args(600))
    return resp


def _install_url(state: str) -> str:
    return f"https://github.com/apps/{config.APP_SLUG}/installations/new?" + urlencode({"state": state})


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str | None = None, state: str | None = None,
                        installation_id: int | None = None):
    expected = request.cookies.get(STATE_COOKIE)
    if not code or not state or not expected or not secrets.compare_digest(state, expected):
        raise HTTPException(400, "로그인 요청이 올바르지 않아요. 처음부터 다시 시도해 주세요.")

    try:
        token = await exchange_code(code, client)
        gh = GitHub(token, client)
        user = await get_user(gh)
        installs = await get_installations(gh)
    except GitHubError:
        raise HTTPException(502, "GitHub와 통신하지 못했어요. 잠시 후 다시 시도해 주세요.")

    # URL로 넘어온 installation_id 는 조작될 수 있으니 실제 내 설치 목록에 있는지 확인
    install_ids = [i["id"] for i in installs]
    if installation_id is not None and installation_id not in install_ids:
        raise HTTPException(403, "확인되지 않은 설치 정보예요.")
    if not install_ids:
        # '바로 로그인'으로 왔는데 아직 설치 전이면 설치 화면으로 이어서 보냄 (새 state)
        new_state = secrets.token_urlsafe(24)
        resp = RedirectResponse(_install_url(new_state))
        resp.set_cookie(STATE_COOKIE, new_state, **_cookie_args(600))
        resp.delete_cookie(RETURNING_COOKIE)
        return resp

    _cleanup()
    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = {"created": time.time(), "login": user["login"], "status": "pending", "result": None}
    task = asyncio.create_task(_analyze(sid, gh, user["login"], install_ids))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    # gh(토큰)는 _analyze 가 끝나면 버려진다. 어디에도 저장하지 않음.

    resp = RedirectResponse("/?view=loading")
    resp.set_cookie(SID_COOKIE, sid, **_cookie_args(config.SESSION_TTL_SEC))
    resp.set_cookie(RETURNING_COOKIE, "1", **_cookie_args(60 * 60 * 24 * 365))
    resp.delete_cookie(STATE_COOKIE)
    return resp


async def _analyze(sid: str, gh: GitHub, login: str, install_ids: list[int]) -> None:
    started = time.time()
    try:
        raw = await collect_all(gh, login, install_ids)
        result = compute(raw)
        result["elapsed_sec"] = round(time.time() - started, 1)
        SESSIONS[sid].update(status="done", result=result)
    except Exception as e:  # noqa: BLE001 — 실패 원인만 남기고 토큰·원본은 남기지 않음
        if sid in SESSIONS:
            SESSIONS[sid].update(status="error", error=type(e).__name__)


@app.post("/auth/logout")
async def logout(request: Request):
    SESSIONS.pop(request.cookies.get(SID_COOKIE, ""), None)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SID_COOKIE)
    return resp


# ---------- 데이터 API ----------

@app.get("/api/wrapped")
async def wrapped(request: Request):
    """status: pending(분석 중) | done | error. 프론트는 1초마다 폴링."""
    s = SESSIONS.get(request.cookies.get(SID_COOKIE, ""))
    if not s:
        raise HTTPException(401, "로그인이 필요해요.")
    body = {"status": s["status"], "login": s["login"]}
    if s["status"] == "done":
        body["data"] = s["result"]
    if s["status"] == "error":
        body["error"] = s.get("error")
    return body


BOJ_PER_MIN = 5                          # 세션당 1분에 조회 가능한 횟수
_BOJ_PUBLIC_KEYS = ("handle", "tier", "solved", "rating", "top_tags", "max_streak", "error")


@app.get("/api/boj")
async def boj(request: Request, handle: str):
    """로그인(GitHub)한 세션에서만 조회. 외부에서 solved.ac 프록시로 쓰이지 않게 막는다 (solved.ac 개발자 약관 제6·7조)."""
    if not HANDLE_RE.match(handle):
        raise HTTPException(400, "백준 아이디 형식이 올바르지 않아요.")
    s = SESSIONS.get(request.cookies.get(SID_COOKIE, ""))
    if not s:
        raise HTTPException(401, "로그인이 필요해요.")
    now = time.time()
    hits = [t for t in s.get("boj_hits", []) if now - t < 60]
    if len(hits) >= BOJ_PER_MIN:
        raise HTTPException(429, "잠시 후 다시 시도해 주세요.")
    s["boj_hits"] = hits + [now]

    out = await fetch_boj(handle, client)
    if out.get("error"):
        # solved.ac 응답 원문·필드 목록은 서버 로그에만 남기고 사용자에게는 보내지 않는다
        log.warning("boj %s: %s %s", out.get("error"), out.get("detail"), out.get("keys"))
    return {k: out[k] for k in _BOJ_PUBLIC_KEYS if k in out}


# ---------- 프론트 ----------
FRONT = Path(__file__).resolve().parents[2] / "prototype"
if FRONT.exists():
    app.mount("/", StaticFiles(directory=FRONT, html=True), name="front")
