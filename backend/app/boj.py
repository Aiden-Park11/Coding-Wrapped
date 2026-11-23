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


def _tag_name(tag) -> str:
    if isinstance(tag, str):
        return tag
    if isinstance(tag, dict):
        for d in tag.get("displayNames", []) or []:
            if d.get("language") == "ko" and d.get("name"):
                return d["name"]
        return _first(tag, "name", "key", "slug") or "?"
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
    return out
