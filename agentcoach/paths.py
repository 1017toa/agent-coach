from __future__ import annotations

import os
from pathlib import Path


def coach_home() -> Path:
    """Where runs, reports and the judge's scratch folder live (never inside a repo)."""
    p = Path(os.environ.get("AGENT_COACH_HOME", Path.home() / ".agent-coach"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def history_dir() -> Path:
    p = coach_home() / "history"
    p.mkdir(exist_ok=True)
    return p


def judge_workdir() -> Path:
    # Folder name contains "agent-coach-judge" so collect.py skips any transcript written here.
    p = coach_home() / "agent-coach-judge"
    p.mkdir(exist_ok=True)
    return p
