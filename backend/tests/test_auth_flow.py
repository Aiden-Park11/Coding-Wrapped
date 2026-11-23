"""로그인 → 콜백 → 분석 → 결과 조회까지 앱 전체 흐름 (가짜 GitHub)."""
import time

import httpx
from fastapi.testclient import TestClient

from app import config, main
from tests import test_github_pipeline as fake


def gh_handler(req: httpx.Request) -> httpx.Response:
    p = req.url.path
    if req.url.host == "github.com" and p == "/login/oauth/access_token":
        return httpx.Response(200, json={"access_token": "ghu_test"})
    if p == "/user":
        return httpx.Response(200, json={"login": fake.LOGIN})
    if p == "/user/installations":
        return httpx.Response(200, json={"installations": [{"id": 42}]})
    return fake.handler(req)


def _setup(monkeypatch):
    monkeypatch.setattr(config, "APP_SLUG", "knu-code-wrapped")
    monkeypatch.setattr(config, "CLIENT_ID", "Iv1.test")
    monkeypatch.setattr(config, "CLIENT_SECRET", "secret")
    monkeypatch.setattr(main, "client", httpx.AsyncClient(transport=httpx.MockTransport(gh_handler)))
    main.SESSIONS.clear()
    return TestClient(main.app, follow_redirects=False)


def test_full_login_flow(monkeypatch):
    c = _setup(monkeypatch)

    r = c.get("/auth/start")
    assert r.status_code == 307
    assert r.headers["location"].startswith("https://github.com/apps/knu-code-wrapped/installations/new?state=")
    state = c.cookies.get("cw_state")

    r = c.get("/auth/callback", params={"code": "abc", "state": state, "installation_id": 42})
    assert r.status_code == 307 and r.headers["location"] == "/?view=loading"
    assert c.cookies.get("cw_sid")

    for _ in range(50):
        body = c.get("/api/wrapped").json()
        if body["status"] != "pending":
            break
        time.sleep(0.05)
    assert body["status"] == "done", body
    assert body["data"]["numbers"]["commits"] == 151

    # 재방문: 설치 화면 대신 바로 승인 화면
    r = c.get("/auth/start")
    assert r.headers["location"].startswith("https://github.com/login/oauth/authorize?")


def test_rejects_bad_state(monkeypatch):
    c = _setup(monkeypatch)
    c.get("/auth/start")
    r = c.get("/auth/callback", params={"code": "abc", "state": "forged"})
    assert r.status_code == 400


def test_rejects_foreign_installation(monkeypatch):
    c = _setup(monkeypatch)
    c.get("/auth/start")
    r = c.get("/auth/callback", params={"code": "abc", "state": c.cookies.get("cw_state"), "installation_id": 999})
    assert r.status_code == 403


def test_public_endpoints(monkeypatch):
    c = _setup(monkeypatch)
    assert c.get("/health").json()["ok"] is True
    assert c.get("/api/wrapped").status_code == 401
    demo = c.get("/api/demo").json()
    assert demo["data"]["numbers"]["commits"] == 1284
    assert c.get("/api/boj", params={"handle": "bad handle!"}).status_code == 400
    assert c.get("/").status_code == 200   # prototype 서빙


def test_boj_requires_session_and_hides_debug(monkeypatch):
    c = _setup(monkeypatch)
    # 로그인 안 한 사람은 solved.ac 조회 불가 (외부 프록시 악용 방지)
    assert c.get("/api/boj", params={"handle": "joon_2026"}).status_code == 401

    async def fake_fetch(handle, client):
        return {"handle": handle, "tier": "Gold IV", "solved": 300, "rating": 1500, "top_tags": None,
                "max_streak": 3, "keys": ["handle", "tier"], "error": None}

    async def broken_fetch(handle, client):
        return {"handle": handle, "tier": None, "solved": None, "rating": None, "top_tags": None,
                "error": "unavailable", "detail": "solved.ac HTTP 401: invalid client"}

    main.SESSIONS["sid1"] = {"created": time.time(), "login": "me", "status": "done", "result": {}}
    c.cookies.set("cw_sid", "sid1")
    monkeypatch.setattr(main, "fetch_boj", fake_fetch)
    body = c.get("/api/boj", params={"handle": "joon_2026"}).json()
    assert body["solved"] == 300 and "keys" not in body and "detail" not in body

    monkeypatch.setattr(main, "fetch_boj", broken_fetch)
    body = c.get("/api/boj", params={"handle": "joon_2026"}).json()
    assert body["error"] == "unavailable" and "detail" not in body

    # 세션당 1분 5회 제한
    codes = [c.get("/api/boj", params={"handle": "joon_2026"}).status_code for _ in range(5)]
    assert codes[-1] == 429
