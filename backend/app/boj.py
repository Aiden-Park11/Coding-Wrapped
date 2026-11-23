"""solved.ac 공개 API로 백준 기록 조회 (로그인 불필요).

⚠️ 엔드포인트 응답 형식은 배포 전에 실제 호출로 한 번 확인할 것.
   실패해도 서비스 전체가 멈추지 않도록 항목별로 None 을 돌려준다.
"""
import re

import httpx

API = "https://solved.ac/api/v3"
HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,20}$")
TIERS = ["Unrated"] + [f"{name} {roman}" for name in
                       ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ruby"]
                       for roman in ["V", "IV", "III", "II", "I"]] + ["Master"]


def tier_name(n: int | None) -> str | None:
    if n is None or not 0 <= n < len(TIERS):
        return None
    return TIERS[n]


def _ko_tag(tag: dict) -> str:
    for d in tag.get("displayNames", []):
        if d.get("language") == "ko":
            return d.get("name")
    return tag.get("key", "?")


async def fetch_boj(handle: str, client: httpx.AsyncClient) -> dict:
    if not HANDLE_RE.match(handle):
        raise ValueError("invalid handle")
    # solved.ac 는 기본 파이썬 User-Agent 요청을 막을 수 있어서 브라우저처럼 보냄
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 coding-wrapped",
        "x-solvedac-language": "ko",
    }
    out = {"handle": handle, "tier": None, "solved": None, "rating": None, "top_tags": None}

    try:
        r = await client.get(f"{API}/user/show", params={"handle": handle}, headers=headers)
        if r.status_code == 404:
            out["error"] = "not_found"
            return out
        if r.status_code >= 400:
            out["error"] = "unavailable"
            out["detail"] = f"solved.ac HTTP {r.status_code}"
            return out
        u = r.json()
        out.update(tier=tier_name(u.get("tier")), solved=u.get("solvedCount"), rating=u.get("rating"))
    except (httpx.HTTPError, ValueError) as e:
        out["error"] = "unavailable"
        out["detail"] = type(e).__name__
        return out

    try:
        r = await client.get(f"{API}/user/problem_tag_stats", params={"handle": handle}, headers=headers)
        r.raise_for_status()
        items = sorted(r.json().get("items", []), key=lambda x: x.get("solved", 0), reverse=True)
        out["top_tags"] = [{"tag": _ko_tag(i["tag"]), "solved": i.get("solved", 0)}
                           for i in items[:4] if i.get("solved")]
    except (httpx.HTTPError, ValueError, KeyError):
        pass
    return out
