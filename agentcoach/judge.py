"""LLM judge: asks the user's own Claude Code or Codex CLI to grade a session.

No API key is involved; we shell out to `claude -p` / `codex exec` so the
user's existing subscription and login are used. Transcripts are redacted
before they are sent, and the judge runs with no tools in a scratch folder
whose transcripts collect.py ignores.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from .collect import Session
from .paths import judge_workdir
from .redact import redact

MAX_TURN_CHARS = 1500
MAX_SESSION_CHARS = 40000   # misses need the whole session, not just its opening


def render_transcript(s: Session) -> str:
    lines = [f"source: {s.source}  project: {s.project}  turns: {len(s.turns)}"]
    budget = MAX_SESSION_CHARS
    for t in s.turns:
        txt = redact(t.text)
        if len(txt) > MAX_TURN_CHARS:
            txt = txt[:MAX_TURN_CHARS] + f"… [+{len(txt) - MAX_TURN_CHARS} chars]"
        img = f" [+{t.images} image]" if t.images else ""
        block = f"\n### USER turn {t.index}{img}\n{txt}\n"
        if t.agent_after:
            block += f"[agent → {redact(t.agent_after)}]\n"
        if len(block) > budget:
            lines.append(f"\n… {len(s.turns) - t.index + 1} more turns omitted")
            break
        budget -= len(block)
        lines.append(block)
    return "".join(lines)


CAUSES = ("prompt_gap", "agent_error", "changed_mind", "external")
SIGNALS = ("correction", "repeat", "redo", "mishap", "ask_back", "frustration")
MISS_ITEM = {
    "type": "object",
    "properties": {
        "turn": {"type": "integer"},
        "signal_turn": {"type": "integer"},
        "signal": {"type": "string", "enum": list(SIGNALS)},
        "cause": {"type": "string", "enum": list(CAUSES)},
        "context_was_enough": {"type": "boolean"},
        "original": {"type": "string"},
        "what_went_wrong": {"type": "string"},
        "better": {"type": "string"},
        "why": {"type": "string"},
    },
    "required": ["turn", "signal_turn", "signal", "cause", "context_was_enough", "original",
                 "what_went_wrong", "better", "why"],
    "additionalProperties": False,
}


def output_schema(rubric: dict) -> dict:
    dim_props = {
        d["id"]: {
            "type": "object",
            "properties": {
                "score": {"type": ["integer", "null"], "enum": [0, 1, 2, None]},
                "evidence_turn": {"type": ["integer", "null"]},
                "note": {"type": "string"},
            },
            "required": ["score", "evidence_turn", "note"],
            "additionalProperties": False,
        }
        for d in rubric["dimensions"]
    }
    return {
        "type": "object",
        "properties": {
            "task_summary": {"type": "string"},
            "dimensions": {"type": "object", "properties": dim_props,
                           "required": list(dim_props), "additionalProperties": False},
            "coaching": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension": {"type": "string", "enum": list(dim_props)},
                        "turn": {"type": "integer"},
                        "original": {"type": "string"},
                        "better": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["dimension", "turn", "original", "better", "why"],
                    "additionalProperties": False,
                },
            },
            "misses": {"type": "array", "maxItems": 8, "items": MISS_ITEM},
        },
        "required": ["task_summary", "dimensions", "coaching", "misses"],
        "additionalProperties": False,
    }


def build_prompt(s: Session, rubric: dict, lang: str = "ko") -> str:
    dims = []
    for d in rubric["dimensions"]:
        guide = " / ".join(f'{g["section"]}: {g["quote"]}' for g in d["guide"])
        dims.append(
            f'- id: {d["id"]} ({d["name"]})\n  what good looks like: {d["summary"]}\n'
            f'  look for: {d["look_for"]}\n  applies when: {d["applies_when"]}\n  guide: {guide}'
        )
    out_lang = "Korean" if lang == "ko" else "English"
    return f"""You are a coach for people who direct AI coding agents (Claude Code, Codex).
Grade ONLY the human's instructions in the transcript below against the official-guide rubric.
The agent's actions appear as one-line [agent → ...] summaries; use them to see consequences
(e.g. the user had to correct something they could have said up front), not to grade the agent.

Scale per dimension: 0 = missed what the guide recommends, 1 = partial or only after correction,
2 = did it from the start, null = not applicable to this conversation. Be strict but fair:
short casual chats legitimately make most dimensions null. Do not reward length for its own sake.
evidence_turn = the USER turn number that best shows the score (null if none).
note = one short sentence in {out_lang} explaining the score, citing what the user wrote or omitted.

coaching = up to 2 of the most valuable rewrites, for the dimensions where the user lost the most.
"original" = a short verbatim excerpt (<=200 chars) of the user's real turn.
"better" = how that same turn should have been written, in the user's own language and tone,
using only facts visible in the transcript (no invented file names; use <placeholders> if needed).
"why" = one sentence in {out_lang} tying the rewrite to the guide.
If nothing is worth coaching, return an empty list.
task_summary = one short line in {out_lang} describing what the session was about.

misses = moments where the user did NOT get what they wanted from a turn (at most 8, most costly first).
Long conversations build context, so a short instruction like "ok do it" / "응 해줘" is fine when context already made
the intent clear; never treat brevity alone as a miss. Evidence comes from what happened next: the user
corrected the result, repeated an earlier instruction, asked to redo/undo, reported damage or an unwanted
action, showed frustration, or the agent had to ask back for missing info.
- turn = the USER turn whose result missed; signal_turn = the USER turn that shows it.
- signal: correction | repeat | redo | mishap | ask_back | frustration
- context_was_enough: true if a careful agent could have inferred the intent from the conversation so far.
- cause: prompt_gap = the intent depended on something only the user knew (a preference, constraint,
  number, scope, where to stop, which item) that the turn didn't say AND context didn't cover;
  agent_error = context/instruction was enough and the agent misread, forgot or ignored it;
  changed_mind = the user decided something new after seeing the result; external = tool/site/login limits.
- original: short verbatim excerpt (<=160 chars) of the missed turn.
- what_went_wrong: one sentence in {out_lang}.
- better: ONLY for prompt_gap, the same turn in the user's own tone adding just the missing piece
  (keep it short; don't restate what context already covered). Empty string for other causes.
- why: one sentence in {out_lang}: for prompt_gap the single missing piece; otherwise why it was not the
  user's prompt problem.
Never copy personal identifiers (names, addresses, ID/phone/card numbers) into any field; write <address>, <name>.

Rubric:
{chr(10).join(dims)}

Transcript:
<<<
{render_transcript(s)}
>>>

Reply with JSON only, matching the provided schema."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def _run_claude(prompt: str, schema: dict, model: str | None, timeout: int) -> dict:
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("claude CLI not found on PATH")
    cmd = [exe, "-p", "--output-format", "json", "--no-session-persistence",
           "--tools", "", "--json-schema", json.dumps(schema)]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       cwd=judge_workdir(), timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude exited {r.returncode}: {(r.stderr or r.stdout)[-400:]}")
    env = json.loads(r.stdout)
    if env.get("is_error"):
        raise RuntimeError(f"claude error: {str(env.get('result'))[:400]}")
    if isinstance(env.get("structured_output"), dict):
        return env["structured_output"]
    return _extract_json(env.get("result", ""))


def _run_codex(prompt: str, schema: dict, model: str | None, timeout: int) -> dict:
    exe = shutil.which("codex")
    if not exe:
        raise RuntimeError("codex CLI not found on PATH")
    with tempfile.TemporaryDirectory(dir=judge_workdir()) as tmp:
        schema_path = os.path.join(tmp, "schema.json")
        out_path = os.path.join(tmp, "out.json")
        with open(schema_path, "w", encoding="utf-8") as fh:
            json.dump(_codex_strict(schema), fh)
        cmd = [exe, "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
               "--output-schema", schema_path, "-o", out_path, "-"]
        if model:
            cmd[2:2] = ["-m", model]
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           cwd=tmp, timeout=timeout)
        if r.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"codex exited {r.returncode}: {(r.stderr or r.stdout)[-400:]}")
        with open(out_path, encoding="utf-8") as fh:
            return _extract_json(fh.read())


def _codex_strict(schema: dict) -> dict:
    """OpenAI structured outputs reject `enum` containing null mixed with type lists; simplify."""
    s = json.loads(json.dumps(schema))

    def walk(node):
        if isinstance(node, dict):
            if node.get("enum") == [0, 1, 2, None]:
                node.pop("enum")
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(s)
    return s


def judge_session(s: Session, rubric: dict, backend: str, model: str | None = None,
                  lang: str = "ko", timeout: int = 600) -> dict:
    schema = output_schema(rubric)
    prompt = build_prompt(s, rubric, lang)
    run = _run_claude if backend == "claude" else _run_codex
    res = run(prompt, schema, model, timeout)
    res["judge"] = f"{backend}:{model or 'default'}"
    _clean(res, rubric)
    return res


def _clean(res: dict, rubric: dict) -> None:
    dims = res.setdefault("dimensions", {})
    for d in rubric["dimensions"]:
        v = dims.get(d["id"]) or {}
        sc = v.get("score")
        v["score"] = sc if sc in (0, 1, 2) else None
        v.setdefault("evidence_turn", None)
        v.setdefault("note", "")
        dims[d["id"]] = v
    res["coaching"] = [c for c in res.get("coaching") or [] if c.get("dimension") in dims][:2]
    misses = []
    for m in res.get("misses") or []:
        if m.get("cause") not in CAUSES:
            continue
        if m["cause"] != "prompt_gap":
            m["better"] = ""          # only the user's own gaps get a rewrite
        misses.append(m)
    res["misses"] = misses[:8]


def judge_many(sessions: list[Session], rubric: dict, backend: str, model: str | None,
               lang: str, workers: int = 3, on_done=None) -> dict[str, dict]:
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_session, s, rubric, backend, model, lang): s for s in sessions}
        for f in as_completed(futs):
            s = futs[f]
            try:
                results[s.id] = f.result()
            except Exception as e:  # keep going; the session falls back to heuristics
                results[s.id] = {"error": str(e)}
            if on_done:
                on_done(s, results[s.id])
    return results


GAP_SCHEMA = {
    "type": "object",
    "properties": {"themes": {"type": "array", "maxItems": 6, "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "items": {"type": "array", "items": {"type": "integer"}},
            "rule": {"type": "string"},
            "where": {"type": "string", "enum": ["CLAUDE.md/AGENTS.md", "memory", "skill", "hook", "prompt"]},
        },
        "required": ["title", "items", "rule", "where"],
        "additionalProperties": False}}},
    "required": ["themes"],
    "additionalProperties": False,
}


def summarize_gaps(gaps: list[dict], backend: str, model: str | None, lang: str = "ko") -> list[dict]:
    """Group prompt gaps that recur across conversations and propose one durable rule per group.

    A gap that keeps coming back ("always use browser X", "affiliation is 'individual'") shouldn't be fixed by typing it
    again every time; it belongs in CLAUDE.md/AGENTS.md, memory, a skill or a hook.
    """
    if len(gaps) < 2:
        return []
    out_lang = "Korean" if lang == "ko" else "English"
    lines = chr(10).join(f"[{i}] ({g['project']}) missing: {g['why']} | turn: {g['original'][:120]}" for i, g in enumerate(gaps))
    prompt = f"""Below are moments where a person's instruction to an AI agent missed one piece of information
only they knew. Group the ones that are the SAME recurring piece of knowledge or preference (it shows up in
2+ items, ideally across different projects). Ignore one-off facts (a single date, a single count).
For each group: title (short, {out_lang}), items (the [index] numbers), rule (one line the person could put
in a persistent instruction file so they never have to say it again, {out_lang}, no personal identifiers),
where (best home: CLAUDE.md/AGENTS.md for project rules, memory for personal facts/preferences, skill for
a repeatable procedure, hook for something that must never be skipped, prompt if it truly varies per task).
Return an empty list if nothing recurs.

{lines}"""
    run = _run_claude if backend == "claude" else _run_codex
    try:
        res = run(prompt, GAP_SCHEMA, model, 300)
    except Exception:
        return []
    themes = []
    for t in res.get("themes") or []:
        idx = [i for i in t.get("items", []) if isinstance(i, int) and 0 <= i < len(gaps)]
        if len(idx) >= 2:
            themes.append({**t, "items": idx})
    return themes
