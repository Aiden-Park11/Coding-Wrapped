"""GitHub API 호출: 토큰 교환, 설치 확인, 레포·커밋·푸시 수집.

주의 (2026-11-21 실측):
- commits API의 `author=` 파라미터는 git 이메일이 계정과 다른 커밋을 빠뜨린다.
  그래서 커밋은 전부 받은 뒤 `author.login`으로 직접 거른다.
"""
import asyncio
import re
from datetime import datetime, timezone

import httpx

from . import config

API = "https://api.github.com"
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class GitHubError(Exception):
    pass


async def exchange_code(code: str, client: httpx.AsyncClient) -> str:
    """OAuth code → 사용자 토큰(ghu_...)"""
    r = await client.post(
        "https://github.com/login/oauth/access_token",
        data={"client_id": config.CLIENT_ID, "client_secret": config.CLIENT_SECRET, "code": code},
        headers={"Accept": "application/json"},
    )
    data = r.json()
    token = data.get("access_token")
    if not token:
        raise GitHubError(f"token exchange failed: {data.get('error', 'unknown')}")
    return token


class GitHub:
    def __init__(self, token: str, client: httpx.AsyncClient):
        self.client = client
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.sem = asyncio.Semaphore(config.CONCURRENCY)

    async def get(self, url: str, params: dict | None = None) -> httpx.Response:
        if not url.startswith("http"):
            url = API + url
        async with self.sem:
            r = await self.client.get(url, params=params, headers=self.headers)
        if r.status_code == 409:      # 빈 레포
            return r
        if r.status_code >= 400:
            raise GitHubError(f"{r.status_code} {url}")
        return r

    async def paginate(self, path: str, params: dict | None = None, key: str | None = None,
                       limit: int = 10_000) -> list:
        """Link 헤더의 next 를 따라가며 최대 limit 개까지 모은다."""
        items: list = []
        url, query = path, {**(params or {}), "per_page": 100}
        while url and len(items) < limit:
            r = await self.get(url, query)
            if r.status_code == 409:
                break
            body = r.json()
            page = body.get(key, []) if key else body
            items.extend(page)
            m = _LINK_NEXT.search(r.headers.get("link", ""))
            url, query = (m.group(1), None) if m else (None, None)
        return items[:limit]


async def get_user(gh: GitHub) -> dict:
    return (await gh.get("/user")).json()


async def get_installations(gh: GitHub) -> list[dict]:
    """이 사용자가 접근 가능한 '우리 앱'의 설치 목록. 콜백의 installation_id 검증에 쓴다."""
    return await gh.paginate("/user/installations", key="installations")


def _year_start() -> datetime:
    return datetime(config.WRAPPED_YEAR, 1, 1, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def list_target_repos(gh: GitHub, installation_ids: list[int]) -> list[dict]:
    """허용된 레포 중 올해 push 가 있고 포크가 아닌 것만."""
    start = _iso(_year_start())
    seen, repos = set(), []
    lists = await asyncio.gather(*[
        gh.paginate(f"/user/installations/{iid}/repositories", key="repositories")
        for iid in installation_ids
    ])
    for repo in (r for lst in lists for r in lst):
        if repo["full_name"] in seen:
            continue
        seen.add(repo["full_name"])
        if repo.get("fork") or (repo.get("pushed_at") or "") < start:
            continue
        repos.append(repo)
    return repos


async def _activity_count(gh: GitHub, full: str, kind: str, login: str) -> int | None:
    """push / force_push 횟수. 권한이나 보관 기간 문제로 실패하면 None."""
    try:
        acts = await gh.paginate(f"/repos/{full}/activity",
                                 {"activity_type": kind, "actor": login}, limit=2000)
    except GitHubError:
        return None
    start = _iso(_year_start())
    return sum(1 for a in acts if (a.get("timestamp") or "") >= start)


async def collect_repo(gh: GitHub, repo: dict, login: str) -> dict:
    full = repo["full_name"]
    since = _iso(_year_start())
    commits, pushes, force_pushes, langs = await asyncio.gather(
        gh.paginate(f"/repos/{full}/commits", {"since": since}, limit=config.MAX_COMMITS_PER_REPO),
        _activity_count(gh, full, "push", login),
        _activity_count(gh, full, "force_push", login),
        gh.get(f"/repos/{full}/languages"),
    )
    me = login.lower()
    mine, other_authors = [], set()
    for c in commits:
        author = ((c.get("author") or {}).get("login") or "").lower()
        if author == me:
            mine.append({
                "repo": full,
                "sha": c["sha"],
                "date": c["commit"]["author"]["date"],
                "message": c["commit"]["message"].split("\n", 1)[0].strip(),
            })
        elif author and not author.endswith("[bot]"):
            other_authors.add(author)
    return {
        "repo": full,
        "private": repo.get("private", False),
        "commits": mine,
        "has_teammates": bool(other_authors),
        "pushes": pushes,
        "force_pushes": force_pushes,
        "languages": langs.json() if langs.status_code == 200 else {},
    }


async def collect_details(gh: GitHub, commits: list[dict]) -> list[dict]:
    """최근 커밋 몇 개만 파일명·변경 줄 수를 조회 (요청 수 제한)."""
    recent = sorted(commits, key=lambda c: c["date"], reverse=True)[: config.MAX_DETAIL_COMMITS]

    async def one(c):
        try:
            d = (await gh.get(f"/repos/{c['repo']}/commits/{c['sha']}")).json()
        except GitHubError:
            return None
        return {
            "lines": (d.get("stats") or {}).get("total", 0),
            "files": [f["filename"] for f in d.get("files", [])],
        }

    return [d for d in await asyncio.gather(*[one(c) for c in recent]) if d]


async def collect_all(gh: GitHub, login: str, installation_ids: list[int]) -> dict:
    repos = await list_target_repos(gh, installation_ids)
    per_repo = await asyncio.gather(*[collect_repo(gh, r, login) for r in repos])
    all_commits = [c for r in per_repo for c in r["commits"]]
    details = await collect_details(gh, all_commits)
    return {"login": login, "repos": per_repo, "details": details}
