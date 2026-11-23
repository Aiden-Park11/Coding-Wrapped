import asyncio

import httpx

from app import boj, config


def _run(handler, monkeypatch, cid="cid", sec="sec"):
    monkeypatch.setattr(config, "SOLVEDAC_CLIENT_ID", cid)
    monkeypatch.setattr(config, "SOLVEDAC_CLIENT_SECRET", sec)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await boj.fetch_boj("joon_2026", c)
    return asyncio.run(go())


def test_sends_app_keys_and_parses(monkeypatch):
    seen = {}

    def h(req):
        seen.update(path=req.url.path, id=req.headers.get("x-client-id"), sec=req.headers.get("x-client-secret"))
        return httpx.Response(200, json={"handle": "joon_2026", "tier": 10, "solvedCount": 213, "rating": 1021,
                                         "tagRatings": [{"tag": {"key": "implementation", "displayNames": [{"language": "ko", "name": "구현"}]}, "solvedCount": 64},
                                                        {"tag": {"key": "math"}, "solvedCount": 28}], "maxStreak": 12})
    out = _run(h, monkeypatch)
    assert seen == {"path": "/api/v4/users/joon_2026", "id": "cid", "sec": "sec"}
    assert out["tier"] == "Silver I" and out["solved"] == 213 and out["rating"] == 1021
    assert out["top_tags"][0] == {"tag": "구현", "solved": 64}
    assert out["top_tags"][1] == {"tag": "수학", "solved": 28}
    assert out["max_streak"] == 12 and "keys" not in out
    assert "error" not in out


def test_not_configured(monkeypatch):
    out = _run(lambda req: httpx.Response(500), monkeypatch, cid="", sec="")
    assert out["error"] == "not_configured"


def test_reports_unknown_shape(monkeypatch):
    out = _run(lambda req: httpx.Response(200, json={"profile": {}}), monkeypatch)
    assert out["error"] == "unparsed" and out["keys"] == ["profile"]


def test_http_error_detail(monkeypatch):
    out = _run(lambda req: httpx.Response(401, text="invalid client"), monkeypatch)
    assert out["error"] == "unavailable" and "401" in out["detail"]


def test_short_tag_keys_real_shape(monkeypatch):
    # 11/23 실제 응답 모양: tagRatings 의 tag 가 짧은 영어 키
    body = {"tier": 5, "solvedCount": 56, "rating": 197, "maxStreak": 7,
            "tagRatings": [{"tag": "impl", "solved": 50}, {"tag": "sim", "solved": 3}]}
    out = _run(lambda req: httpx.Response(200, json=body), monkeypatch)
    assert out["tier"] == "Bronze I" and out["solved"] == 56
    assert [t["tag"] for t in out["top_tags"]] == ["구현", "시뮬레이션"]
