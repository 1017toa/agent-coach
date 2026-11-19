"""Weekly ranking: a score that rewards prompting well, with a small bonus for using agents a lot.

    weekly score = quality x activity bonus
    quality      = mean session score (0-100) over LLM-graded conversations in the window
    bonus        = 1.0 for one conversation, rising slowly, capped at 1.3 from 20 conversations

Only numbers and a nickname you choose ever leave your machine; no prompts, projects or paths.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

from . import __version__

SCHEMA = 1
MIN_CONVERSATIONS = 3
BONUS_CAP = 0.3
BONUS_FULL_AT = 20
WINDOW_DAYS = 7


def activity_bonus(n: int) -> float:
    if n <= 1:
        return 1.0
    return round(1 + BONUS_CAP * min(1.0, math.log(n) / math.log(BONUS_FULL_AT)), 3)


def session_score(s: dict) -> float | None:
    vals = [v.get("score") for v in (s.get("dimensions") or {}).values() if v.get("score") is not None]
    return sum(vals) / (2 * len(vals)) * 100 if vals else None


def _ts(s: str) -> datetime | None:
    try:
        d = datetime.fromisoformat((s or "").replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def window_sessions(runs: list[dict], end: datetime, days: int = WINDOW_DAYS) -> list[dict]:
    """LLM-graded sessions whose last activity falls in (end - days, end]; the latest grading wins."""
    start = end - timedelta(days=days)
    seen: dict[str, dict] = {}
    for run in runs:
        for s in run.get("sessions", []):
            judge = s.get("judge") or run.get("judge") or ""
            if not judge.startswith(("claude", "codex")):
                continue   # offline keyword scores aren't comparable across people
            t = _ts(s.get("ended") or s.get("started"))
            if t and start < t <= end:
                seen[s["id"]] = {**s, "_run_lang": run.get("lang")}
    return list(seen.values())


def weekly(runs: list[dict], rubric: dict, end: datetime | None = None, days: int = WINDOW_DAYS) -> dict:
    end = end or datetime.now(timezone.utc)
    sess = window_sessions(runs, end, days)
    scores = [x for x in (session_score(s) for s in sess) if x is not None]
    n = len(scores)
    quality = round(sum(scores) / n, 1) if n else None
    bonus = activity_bonus(n)
    habits = {}
    for d in rubric["dimensions"]:
        vals = [s["dimensions"][d["id"]]["score"] for s in sess
                if (s.get("dimensions") or {}).get(d["id"], {}).get("score") is not None]
        habits[d["id"]] = round(sum(vals) / (2 * len(vals)) * 100) if vals else None
    prev = None
    if days:
        p_sess = window_sessions(runs, end - timedelta(days=days), days)
        p_scores = [x for x in (session_score(s) for s in p_sess) if x is not None]
        if len(p_scores) >= MIN_CONVERSATIONS:
            prev = round(sum(p_scores) / len(p_scores), 1)
    iso = end.isocalendar()
    return {
        "week": f"{iso[0]}-W{iso[1]:02d}",
        "window_end": end.isoformat(timespec="seconds"),
        "days": days,
        "conversations": n,
        "quality": quality,
        "bonus": bonus,
        "score": round(quality * bonus, 1) if quality is not None else None,
        "eligible": n >= MIN_CONVERSATIONS,
        "prev_quality": prev,
        "improvement": round(quality - prev, 1) if (quality is not None and prev is not None) else None,
        "habits": habits,
        "sources": sorted({s.get("source", "") for s in sess} - {""}),
        "rubric_version": rubric.get("version"),
    }


def payload(w: dict, nickname: str, league: str = "") -> dict:
    """What a submission contains. Numbers and a self-chosen nickname only."""
    return {
        "schema": SCHEMA, "tool": "agent-coach", "version": __version__,
        "nickname": nickname[:32], "league": league[:32],
        "week": w["week"], "conversations": w["conversations"], "quality": w["quality"],
        "bonus": w["bonus"], "score": w["score"], "improvement": w["improvement"],
        "habits": w["habits"], "sources": w["sources"], "rubric_version": w["rubric_version"],
    }


def issue_url(repo: str, p: dict) -> str:
    from urllib.parse import quote
    title = f"[rank] {p['week']} {p['nickname']}"
    body = ("Weekly ranking submission from `agent-coach rank`. Submit as is; a bot validates it "
            "and adds it to the leaderboard.\n\n```json\n" + json.dumps(p, ensure_ascii=False, indent=1) + "\n```\n")
    return f"https://github.com/{repo}/issues/new?title={quote(title)}&body={quote(body)}"
