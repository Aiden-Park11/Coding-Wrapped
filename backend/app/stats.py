"""수집한 원본 데이터 → 카드에 들어갈 통계. 외부 호출 없는 순수 함수만 둔다."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from statistics import median

KST = timezone(timedelta(hours=9))
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
NIGHT_HOURS = {21, 22, 23, 0, 1, 2, 3, 4, 5}


def to_kst(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KST)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def longest_streak(days: set[date]) -> int:
    best = cur = 0
    prev = None
    for d in sorted(days):
        cur = cur + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, cur)
        prev = d
    return best


def heatmap(times: list[datetime]) -> dict:
    """요일 7줄 × 2시간 단위 12칸. level 은 0~4."""
    grid = [[0] * 12 for _ in range(7)]
    for t in times:
        grid[t.weekday()][t.hour // 2] += 1
    peak = max((v for row in grid for v in row), default=0)
    levels = [[0 if v == 0 else min(4, 1 + int(3 * v / peak)) for v in row] for row in grid] if peak else grid
    return {"days": DAYS, "counts": grid, "levels": levels}


def top_messages(messages: list[str], n: int = 5) -> list[dict]:
    norm = [" ".join(m.lower().split()) for m in messages if m.strip()]
    return [{"message": m, "count": c} for m, c in Counter(norm).most_common(n)]


# 코딩 유형: 각 축 0~1, 1에 가까울수록 오른쪽 성향
AXES = [
    ("time", "아침형", "야행성", "D", "N"),
    ("rhythm", "꾸준한", "몰아치기", "S", "B"),
    ("collab", "팀플", "솔로", "T", "S"),
    ("size", "커밋 장인", "리팩토러", "C", "L"),
]
TYPE_LINES = {
    "time": ("해가 떠 있을 때", "모두가 잠든 새벽,"),
    "rhythm": ("조금씩 꾸준히 쌓아 올려요.", "마감 직전에 몰아쳐서 끝내요."),
    "collab": ("팀원들과 함께 레포를 키우며", "혼자 끝까지 파고들며"),
    "size": ("작고 깔끔한 커밋을 남기는 편이에요.", "한 번에 크게 갈아엎는 편이에요."),
}


def coding_type(times: list[datetime], day_counts: Counter, commits_per_push: float | None,
                median_lines: float | None, solo_share: float) -> dict:
    total = len(times)
    night = sum(1 for t in times if t.hour in NIGHT_HOURS) / total if total else 0.5

    # 몰아치기: 가장 바쁜 상위 20% 날짜에 커밋이 얼마나 몰렸나
    if len(day_counts) >= 5:
        busiest = sorted(day_counts.values(), reverse=True)[: max(1, len(day_counts) // 5)]
        burst = _clamp((sum(busiest) / total - 0.2) / 0.6)
    else:
        burst = 0.5

    # 커밋 크기: 변경 줄 수 중앙값 우선, 없으면 푸시당 커밋 수
    if median_lines is not None:
        size = _clamp(median_lines / 200)
    elif commits_per_push is not None:
        size = _clamp((commits_per_push - 1) / 4)
    else:
        size = 0.5

    scores = {"time": night, "rhythm": burst, "collab": solo_share, "size": size}
    code, words, lines, axes = [], [], [], []
    for key, left, right, lc, rc in AXES:
        s = scores[key]
        is_right = s >= 0.5
        code.append(rc if is_right else lc)
        words.append(right if is_right else left)
        lines.append(TYPE_LINES[key][1 if is_right else 0])
        axes.append({"key": key, "left": left, "right": right, "score": round(s, 2)})
    return {
        "code": "·".join(code),
        "name": " ".join(words),
        "description": " ".join(lines),
        "axes": axes,
    }


def compute(raw: dict, today: date | None = None) -> dict:
    repos = raw["repos"]
    commits = [c for r in repos for c in r["commits"]]
    times = [to_kst(c["date"]) for c in commits]
    total = len(commits)

    year = times[0].year if times else (today or date.today()).year
    today = today or datetime.now(KST).date()
    elapsed = max(1, (min(today, date(year, 12, 31)) - date(year, 1, 1)).days + 1)

    day_counts = Counter(t.date() for t in times)

    # 언어: 레포별 언어 비율 × 그 레포의 내 커밋 수
    lang_weight: Counter = Counter()
    for r in repos:
        n = len(r["commits"])
        size = sum(r["languages"].values())
        if n and size:
            for lang, b in r["languages"].items():
                lang_weight[lang] += n * b / size
    main_lang = None
    if lang_weight:
        lang, w = lang_weight.most_common(1)[0]
        main_lang = {"name": lang, "percent": round(100 * w / sum(lang_weight.values()))}

    # 푸시: 일부 레포에서 조회 실패하면 None 이 섞여 있을 수 있음
    push_vals = [r["pushes"] for r in repos if r["pushes"] is not None]
    pushes = sum(push_vals) if push_vals else None
    force_vals = [r["force_pushes"] for r in repos if r["force_pushes"] is not None]
    force_pushes = sum(force_vals) if force_vals else None
    commits_per_push = round(total / pushes, 1) if pushes else None

    details = raw.get("details", [])
    median_lines = median([d["lines"] for d in details]) if details else None
    file_counts = Counter(f for d in details for f in d["files"])
    most_rewritten = None
    if file_counts:
        name, cnt = file_counts.most_common(1)[0]
        most_rewritten = {"file": name.rsplit("/", 1)[-1], "count": cnt, "sample_size": len(details)}

    mine_solo = sum(len(r["commits"]) for r in repos if not r["has_teammates"])
    solo_share = mine_solo / total if total else 0.5

    messages = [c["message"] for c in commits]
    night_share = sum(1 for t in times if t.hour < 4) / total if total else 0

    return {
        "login": raw["login"],
        "year": year,
        "enough_data": total >= 10,
        "numbers": {
            "commits": total,
            "repos": sum(1 for r in repos if r["commits"]),
            "active_days": len(day_counts),
            "daily_avg": round(total / elapsed, 1),
            "longest_streak": longest_streak(set(day_counts)),
            "main_language": main_lang,
            "pushes": pushes,
            "force_pushes": force_pushes,
            "commits_per_push": commits_per_push,
        },
        "time": {
            "heatmap": heatmap(times),
            "night_share_0_4": round(100 * night_share),
            "peak_hour": Counter(t.hour for t in times).most_common(1)[0][0] if times else None,
        },
        "messages": {
            "top": top_messages(messages),
            "shortest": min(messages, key=len) if messages else None,
            "most_rewritten": most_rewritten,
        },
        "type": coding_type(times, day_counts, commits_per_push, median_lines, solo_share),
    }
