"""solved.ac 공식 API v4 로 백준 공개 프로필 조회.

- 모든 요청에 앱 키(x-client-id / x-client-secret) 필요 → 키는 서버(.env)에만 둔다.
- 공개 프로필은 사용자 로그인 토큰 없이 앱 키만으로 조회 (GET /api/v4/users/{handle}).
- 응답 필드 이름은 공식 문서로 최종 확인 필요 → 여러 후보 이름을 받아 주고,
  못 읽으면 응답의 키 목록(keys)을 같이 돌려줘서 바로 고칠 수 있게 한다.
"""
import re

import httpx

from . import config

API = "https://solved.ac/api/v4"
HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,20}$")
TIERS = ["Unrated"] + [f"{name} {roman}" for name in
                       ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ruby"]
                       for roman in ["V", "IV", "III", "II", "I"]] + ["Master"]


def tier_name(t) -> str | None:
    if isinstance(t, int):
        return TIERS[t] if 0 <= t < len(TIERS) else None
    if isinstance(t, str):
        return t
    if isinstance(t, dict):
        for k in ("name", "label", "title"):
            if isinstance(t.get(k), str):
                return t[k]
        for k in ("level", "value", "tier"):
            if isinstance(t.get(k), int):
                return tier_name(t[k])
    return None


def _first(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _number(v):
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, dict):
        return _first(v, "total", "value", "rating", "count")
    return None


# v4 tagRatings 는 짧은 영어 키(impl, sim ...)로 와서 한글로 바꿔 줌
KO_TAGS = {
    "impl": "구현", "implementation": "구현", "math": "수학", "string": "문자열", "sim": "시뮬레이션",
    "simulation": "시뮬레이션", "greedy": "그리디", "bfs": "BFS", "dfs": "DFS", "dp": "DP",
    "graphs": "그래프", "graph_traversal": "그래프 탐색", "bruteforcing": "브루트포스", "sorting": "정렬",
    "ds": "자료구조", "data_structures": "자료구조", "arithmetic": "사칙연산", "number_theory": "정수론",
    "binary_search": "이분 탐색", "geometry": "기하", "trees": "트리", "combinatorics": "조합론",
    "prefix_sum": "누적 합", "backtracking": "백트래킹", "dijkstra": "데이크스트라", "recursion": "재귀",
    "stack": "스택", "queue": "큐", "hashing": "해싱", "two_pointer": "투 포인터", "bitmask": "비트마스킹",
    "set": "집합", "priority_queue": "우선순위 큐", "case_work": "많은 조건 분기", "parsing": "파싱",
}


def _tag_name(tag) -> str:
    if isinstance(tag, str):
        return KO_TAGS.get(tag, tag)
    if isinstance(tag, dict):
        for d in tag.get("displayNames", []) or []:
            if d.get("language") == "ko" and d.get("name"):
                return d["name"]
        key = _first(tag, "key", "name", "slug") or "?"
        return KO_TAGS.get(key, key)
    return "?"


def _top_tags(u: dict) -> list | None:
    for key in ("tagRatings", "tag_ratings", "tags", "tagStats"):
        items = u.get(key)
        if isinstance(items, dict):
            items = _first(items, "items", "data")
        if not isinstance(items, list):
            continue
        out = []
        for i in items:
            if not isinstance(i, dict):
                continue
            solved = _number(_first(i, "solved", "solvedCount", "count"))
            if solved:
                out.append({"tag": _tag_name(_first(i, "tag", "name", "key")), "solved": solved})
        if out:
            return sorted(out, key=lambda x: x["solved"], reverse=True)[:4]
    return None


def parse_user(body) -> dict:
    u = body.get("data", body) if isinstance(body, dict) else {}
    u = u.get("user", u) if isinstance(u.get("user"), dict) else u
    return {
        "tier": tier_name(u.get("tier")),
        "solved": _number(_first(u, "solvedCount", "solved_count", "solved")),
        "rating": _number(u.get("rating")),
        "top_tags": _top_tags(u),
        "max_streak": _number(u.get("maxStreak")),
        "keys": sorted(u.keys())[:40],
    }


async def fetch_boj(handle: str, client: httpx.AsyncClient) -> dict:
    if not HANDLE_RE.match(handle):
        raise ValueError("invalid handle")
    out = {"handle": handle, "tier": None, "solved": None, "rating": None, "top_tags": None}
    if not (config.SOLVEDAC_CLIENT_ID and config.SOLVEDAC_CLIENT_SECRET):
        out["error"] = "not_configured"
        return out
    headers = {
        "Accept": "application/json",
        "x-client-id": config.SOLVEDAC_CLIENT_ID,
        "x-client-secret": config.SOLVEDAC_CLIENT_SECRET,
        "User-Agent": "coding-wrapped/0.1 (+https://github.com/Aiden-Park11/Coding-Wrapped)",
    }
    try:
        r = await client.get(f"{API}/users/{handle}", headers=headers)
    except httpx.HTTPError as e:
        out.update(error="unavailable", detail=type(e).__name__)
        return out
    if r.status_code == 404:
        out["error"] = "not_found"
        return out
    if r.status_code >= 400:
        out.update(error="unavailable", detail=f"solved.ac HTTP {r.status_code}: {r.text[:200]}")
        return out
    try:
        out.update(parse_user(r.json()))
    except ValueError:
        out.update(error="unavailable", detail="응답이 JSON 이 아님")
        return out
    if out["solved"] is None:
        out["error"] = "unparsed"
        out["detail"] = "응답은 받았지만 해결 수 필드를 못 찾음 → keys 확인"
    else:
        out.pop("keys", None)   # 정상일 땐 디버깅용 키 목록 숨김
    return out
