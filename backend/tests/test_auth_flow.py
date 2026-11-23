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
