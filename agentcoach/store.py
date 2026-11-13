"""Run records: one JSON file per scoring run under ~/.agent-coach/history/.

Transcripts get deleted by the tools themselves (Claude Code keeps 30 days by
default), so each run stores everything the report needs: scores, notes and
the short coaching excerpts. Nothing here is ever uploaded.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .collect import Session
from .paths import history_dir
from .redact import redact


def aggregate(results: list[dict], rubric: dict) -> dict:
    out = {}
    for d in rubric["dimensions"]:
        scores = [r["dimensions"][d["id"]]["score"] for r in results
                  if r.get("dimensions", {}).get(d["id"], {}).get("score") is not None]
        out[d["id"]] = {
            "score": round(sum(scores) / (2 * len(scores)) * 100) if scores else None,
            "n": len(scores),
            "missed": sum(1 for x in scores if x == 0),
        }
    vals = [v["score"] for v in out.values() if v["score"] is not None]
    return {"overall": round(sum(vals) / len(vals)) if vals else None, "dimensions": out}


def miss_summary(sessions: list[dict]) -> dict:
    """How often the user didn't get what they wanted, and how much of that was their own prompt gap."""
    by_cause: dict[str, int] = {}
    turns = 0
    for s in sessions:
        turns += s.get("turns", 0)
        for m in s.get("misses", []):
            by_cause[m["cause"]] = by_cause.get(m["cause"], 0) + 1
    total = sum(by_cause.values())
    gaps = by_cause.get("prompt_gap", 0)
    return {"total": total, "by_cause": by_cause, "turns": turns,
            "gap_share": round(gaps / total * 100) if total else None,
            "gaps_per_100_turns": round(gaps / turns * 100, 1) if turns else None,
            "themes": []}


def build_run(sessions: list[Session], results: dict[str, dict], rubric: dict,
              window_start: str | None, judge: str) -> dict:
    per = []
    for s in sessions:
        r = results.get(s.id)
        if not r or "dimensions" not in r:
            continue
        turns = {t.index: t for t in s.turns}
        dims = r["dimensions"]
        for v in dims.values():
            t = turns.get(v.get("evidence_turn") or -1)
            v["excerpt"] = redact(t.text[:220]) if t else ""
        per.append({
            "id": s.id, "source": s.source, "project": s.project,
            "started": s.started, "ended": s.ended, "turns": len(s.turns),
            "task_summary": redact(r.get("task_summary", "")),
            "judge": r.get("judge", judge),
            "dimensions": dims,
            "coaching": [{**c, "original": redact(c.get("original", "")),
                          "better": redact(c.get("better", ""))} for c in r.get("coaching", [])],
            "misses": [{**m, **{k: redact(m.get(k, "")) for k in ("original", "better", "what_went_wrong", "why")}}
                       for m in r.get("misses", [])],
        })
    agg = aggregate(per, rubric)
    agg["misses"] = miss_summary(per)
    now = datetime.now().astimezone()
    return {
        "schema": 1,
        "created": now.isoformat(timespec="seconds"),
        "window_start": window_start,
        "judge": judge,
        "rubric": {"id": rubric["id"], "version": rubric.get("version", 1)},
        "sources": sorted({p["source"] for p in per}),
        "session_count": len(per),
        **agg,
        "sessions": per,
    }


def save_run(run: dict) -> Path:
    stamp = run["created"].replace(":", "").replace("-", "")[:15]
    path = history_dir() / f"run-{stamp}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load_runs() -> list[dict]:
    runs = []
    for p in sorted(history_dir().glob("run-*.json")):
        try:
            runs.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    runs.sort(key=lambda r: r["created"])
    return runs
