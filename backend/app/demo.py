"""발표·테스트용 데모 데이터 (프로토타입과 같은 숫자). 실제 API 응답과 같은 모양."""
from .stats import DAYS

_BASE = [4, 4, 3, 1, 0, 0, 1, 2, 2, 2, 3, 4]


def _levels():
    rows = []
    for r in range(7):
        row = []
        for c in range(12):
            x = _BASE[c]
            if r >= 5 and 6 <= c <= 9:
                x += 1
            if r >= 5 and c <= 1:
                x -= 1
            if (r * 5 + c * 3) % 7 == 0:
                x -= 1
            if r == 3 and c <= 2:
                x = 4
            row.append(max(0, min(4, x)))
        rows.append(row)
    return rows


DEMO_WRAPPED = {
    "login": "demo-user",
    "year": 2026,
    "enough_data": True,
    "demo": True,
    "numbers": {
        "commits": 1284, "repos": 14, "active_days": 201, "daily_avg": 3.9, "longest_streak": 23,
        "main_language": {"name": "C", "percent": 62},
        "pushes": 312, "force_pushes": 7, "commits_per_push": 4.1,
    },
    "time": {
        "heatmap": {"days": DAYS, "counts": None, "levels": _levels()},
        "night_share_0_4": 38,
        "peak_hour": 2,
    },
    "messages": {
        "top": [{"message": "fix", "count": 83}, {"message": "수정", "count": 41},
                {"message": "진짜 마지막", "count": 12}, {"message": "제발", "count": 9},
                {"message": "왜 됨?", "count": 3}],
        "shortest": "ㅁ",
        "most_rewritten": {"file": "main.c", "count": 97, "sample_size": 60},
    },
    "type": {
        "code": "N·B·S·L",
        "name": "야행성 몰아치기 솔로 리팩토러",
        "description": "모두가 잠든 새벽, 마감 직전에 몰아쳐서 끝내요. 혼자 끝까지 파고들며 한 번에 크게 갈아엎는 편이에요.",
        "axes": [
            {"key": "time", "left": "아침형", "right": "야행성", "score": 0.78},
            {"key": "rhythm", "left": "꾸준한", "right": "몰아치기", "score": 0.64},
            {"key": "collab", "left": "팀플", "right": "솔로", "score": 0.83},
            {"key": "size", "left": "커밋 장인", "right": "리팩토러", "score": 0.71},
        ],
    },
}

DEMO_BOJ = {
    "handle": "demo", "tier": "Silver I", "solved": 213, "rating": 1021,
    "top_tags": [{"tag": "구현", "solved": 64}, {"tag": "그리디 알고리즘", "solved": 31},
                 {"tag": "수학", "solved": 28}, {"tag": "너비 우선 탐색", "solved": 17}],
}
