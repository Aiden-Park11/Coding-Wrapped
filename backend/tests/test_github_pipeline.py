"""가짜 GitHub API(MockTransport)로 수집 파이프라인 전체를 검증한다. 네트워크 사용 없음."""
import asyncio

import httpx

from app import config
from app.github import GitHub, collect_all
from app.stats import compute

LOGIN = "Aiden-Park11"


def _c(sha, login, date, msg):
    return {"sha": sha, "author": {"login": login} if login else None,
            "commit": {"author": {"date": date}, "message": msg}}


REPOS = [
    {"full_name": "me/new", "fork": False, "private": True, "pushed_at": "2026-11-20T00:00:00Z"},
    {"full_name": "me/old", "fork": False, "private": False, "pushed_at": "2025-12-01T00:00:00Z"},   # 작년 → 제외
    {"full_name": "me/forked", "fork": True, "private": False, "pushed_at": "2026-06-01T00:00:00Z"},  # 포크 → 제외
    {"full_name": "team/game", "fork": False, "private": False, "pushed_at": "2026-10-31T00:00:00Z"},
]

# me/new: 커밋 150개 → 페이지 2장. author.login 이 내 아이디가 아닌 커밋(이메일 불일치 등) 포함
NEW_COMMITS = [_c(f"n{i}", LOGIN if i % 3 else "aiden-park11", f"2026-0{1 + i % 9}-1{i % 9}T15:00:00Z", "fix")
               for i in range(150)] + [_c("x1", None, "2026-02-01T00:00:00Z", "unlinked email")]
GAME_COMMITS = [_c("g1", "icrf-hot", "2026-10-28T12:00:00Z", "add sfx"),
                _c("g2", LOGIN, "2026-10-29T13:00:00Z", "fix jump"),
                _c("g3", "dependabot[bot]", "2026-10-29T14:00:00Z", "bump")]

calls: list[str] = []


def handler(req: httpx.Request) -> httpx.Response:
    path, q = req.url.path, dict(req.url.params)
    calls.append(path)
    assert req.headers["authorization"] == "Bearer ghu_test"
    if path == "/user/installations/42/repositories":
        return httpx.Response(200, json={"repositories": REPOS})
    if path == "/repos/me/new/commits":
        assert "author" not in q  # author 필터를 쓰지 않아야 함
        page = int(q.get("page", 1))
        chunk = NEW_COMMITS[(page - 1) * 100: page * 100]
        headers = {}
        if page == 1:
            headers["link"] = '<https://api.github.com/repos/me/new/commits?since=2026-01-01T00:00:00Z&per_page=100&page=2>; rel="next"'
        return httpx.Response(200, json=chunk, headers=headers)
    if path == "/repos/team/game/commits":
        return httpx.Response(200, json=GAME_COMMITS)
    if path.endswith("/activity"):
        if q["activity_type"] == "push":
            acts = [{"timestamp": "2026-03-01T00:00:00Z"}] * 30 + [{"timestamp": "2025-12-31T00:00:00Z"}]
            return httpx.Response(200, json=acts if "me/new" in path else [])
        return httpx.Response(403, json={"message": "forbidden"}) if "team" in path else httpx.Response(200, json=[])
    if path.endswith("/languages"):
        return httpx.Response(200, json={"C": 800, "Python": 200} if "me/new" in path else {"C#": 1000})
    if "/commits/" in path:
        return httpx.Response(200, json={"stats": {"total": 40}, "files": [{"filename": "src/main.c"}]})
    raise AssertionError(f"unexpected call {path}")


def test_pipeline_end_to_end():
    config.WRAPPED_YEAR = 2026
    calls.clear()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await collect_all(GitHub("ghu_test", client), LOGIN, [42])

    raw = asyncio.run(run())

    # 작년 레포·포크는 아예 호출하지 않음
    assert not any("/repos/me/old" in c or "/repos/me/forked" in c for c in calls)
    by_repo = {r["repo"]: r for r in raw["repos"]}
    assert set(by_repo) == {"me/new", "team/game"}

    # 페이지네이션 2장 + 대소문자 다른 login 도 내 커밋, author 가 없는 커밋은 제외
    assert len(by_repo["me/new"]["commits"]) == 150
    assert by_repo["me/new"]["has_teammates"] is False
    # 팀 레포: 내 커밋만, 봇은 팀원으로 치지 않음
    assert [c["sha"] for c in by_repo["team/game"]["commits"]] == ["g2"]
    assert by_repo["team/game"]["has_teammates"] is True
    # 푸시: 작년 기록 제외 / 권한 없으면 None
    assert by_repo["me/new"]["pushes"] == 30
    assert by_repo["team/game"]["force_pushes"] is None
    # 상세 조회는 MAX_DETAIL_COMMITS 개까지만
    assert len(raw["details"]) == config.MAX_DETAIL_COMMITS

    out = compute(raw)
    assert out["numbers"]["commits"] == 151
    assert out["numbers"]["pushes"] == 30
    assert out["messages"]["most_rewritten"]["file"] == "main.c"
    assert out["enough_data"] is True
