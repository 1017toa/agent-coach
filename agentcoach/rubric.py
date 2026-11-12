from __future__ import annotations

import json
from importlib import resources
from pathlib import Path


def load_rubric(path: str | None = None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.loads(resources.files("agentcoach").joinpath("rubric/default.json").read_text(encoding="utf-8"))


def dim_ids(rubric: dict) -> list[str]:
    return [d["id"] for d in rubric["dimensions"]]
