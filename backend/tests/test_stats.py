from datetime import date

from app.stats import compute, longest_streak, to_kst


def _commit(iso, msg="fix", repo="me/a"):
    return {"repo": repo, "sha": iso, "date": iso, "message": msg}


def _raw(commits_by_repo, teammates=None, pushes=None, langs=None, details=None):
    teammates = teammates or {}
    return {
        "login": "joon",
        "repos": [
            {"repo": r, "private": False, "commits": cs, "has_teammates": teammates.get(r, False),
             "pushes": (pushes or {}).get(r), "force_pushes": 0,
             "languages": (langs or {}).get(r, {})}
            for r, cs in commits_by_repo.items()
        ],
        "details": details or [],
    }


def test_utc_to_kst():
    # 01:48 UTC = 10:48 KST (11/21 실측 push 시각)
    t = to_kst("2026-11-21T01:48:38Z")
    assert (t.hour, t.minute) == (10, 48)


def test_kst_date_rollover():
    # UTC 20:00 은 한국 시간으로 다음날 05:00
    t = to_kst("2026-03-01T20:00:00Z")
    assert t.date() == date(2026, 3, 2) and t.hour == 5


def test_longest_streak():
    days = {date(2026, 1, d) for d in (1, 2, 3, 5, 6, 7, 8, 10)}
    assert longest_streak(days) == 4


def test_compute_basic_numbers_and_messages():
    commits = [
        _commit("2026-03-01T17:30:00Z", "fix"),      # KST 02:30 (새벽)
        _commit("2026-03-01T18:00:00Z", "Fix  "),    # KST 03:00, 정규화되면 fix
        _commit("2026-03-02T05:00:00Z", "add login"),  # KST 14:00
        _commit("2026-03-03T05:00:00Z", "ㅁ"),
    ]
    out = compute(_raw({"me/a": commits}, pushes={"me/a": 2}, langs={"me/a": {"C": 900, "Python": 100}}),
                  today=date(2026, 12, 31))
    n = out["numbers"]
    assert n["commits"] == 4 and n["repos"] == 1 and n["active_days"] == 2  # 3/1 17:30 UTC 는 한국 3/2
    assert n["longest_streak"] == 2
    assert n["main_language"] == {"name": "C", "percent": 90}
    assert n["commits_per_push"] == 2.0
    assert out["messages"]["top"][0] == {"message": "fix", "count": 2}
    assert out["messages"]["shortest"] == "ㅁ"
    assert out["time"]["night_share_0_4"] == 50
    assert out["enough_data"] is False
    hm = out["time"]["heatmap"]
    assert len(hm["levels"]) == 7 and all(len(r) == 12 for r in hm["levels"])


def test_solo_vs_team_axis():
    solo = [_commit(f"2026-04-0{i}T03:00:00Z", repo="me/solo") for i in range(1, 9)]
    team = [_commit(f"2026-05-0{i}T03:00:00Z", repo="org/team") for i in range(1, 3)]
    out = compute(_raw({"me/solo": solo, "org/team": team}, teammates={"org/team": True}),
                  today=date(2026, 12, 31))
    axis = {a["key"]: a for a in out["type"]["axes"]}
    assert axis["collab"]["score"] == 0.8
    assert "솔로" in out["type"]["name"]


def test_empty_user_does_not_crash():
    out = compute(_raw({}), today=date(2026, 11, 21))
    assert out["numbers"]["commits"] == 0
    assert out["messages"]["shortest"] is None
    assert out["type"]["code"].count("·") == 3
