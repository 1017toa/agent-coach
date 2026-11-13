from __future__ import annotations

import copy
import json
from importlib import resources
from pathlib import Path


def load_rubric(path: str | None = None, lang: str = "ko") -> dict:
    if path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        raw = json.loads(resources.files("agentcoach").joinpath("rubric/default.json").read_text(encoding="utf-8"))
    return localize(raw, lang)


def localize(rubric: dict, lang: str) -> dict:
    """Return a copy whose user-facing fields are in `lang`.

    Korean is the base text; any `*_en` field or per-dimension `en` block overrides it for English.
    A custom rubric with no English fields simply stays as written.
    """
    r = copy.deepcopy(rubric)
    r["lang"] = lang
    for g in (g for d in r["dimensions"] for g in d.get("guide", [])):
        g.setdefault("quote", g.pop("quote_ko", ""))
    if lang != "en":
        return r
    r["title"] = r.get("title_en", r["title"])
    r["scale"] = r.get("scale_en", r.get("scale"))
    for src in r.get("sources", {}).values():
        src["title"] = src.get("title_en", src["title"])
        src["url"] = src.get("url_en", src["url"])
    for d in r["dimensions"]:
        en = d.get("en") or {}
        for k in ("name", "short", "summary", "example"):
            if k in en:
                d[k] = en[k]
        for g in d.get("guide", []):
            g["quote"] = g.get("quote_en", g["quote"])
            g["section"] = g.get("section_en", g["section"])
    return r


def dim_ids(rubric: dict) -> list[str]:
    return [d["id"] for d in rubric["dimensions"]]
