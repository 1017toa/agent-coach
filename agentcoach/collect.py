"""Read local Claude Code and Codex CLI transcripts into a common shape.

Only the human side matters for coaching, so a Session keeps the user's
prompts verbatim and squeezes everything the agent did between them into a
one-line summary (tool counts + a short excerpt of its last reply).
"""
from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .paths import coach_home


@dataclass
class Turn:
    index: int
    text: str
    ts: str = ""
    images: int = 0
    slash: str = ""           # e.g. "/clear" when the turn was a slash command
    agent_after: str = ""     # summary of what the agent did before the next human turn


@dataclass
class Session:
    source: str               # "claude" | "codex"
    id: str
    project: str
    path: str
    started: str
    ended: str
    turns: list[Turn] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- helpers

_NOISE_PREFIXES = (
    "<local-command-", "<command-message>", "<task-notification", "<system-reminder",
    "<side-sessions-event", "<ci-monitor-event", "Caveat:", "[Request interrupted",
    "<environment_context>", "<user_instructions>", "# AGENTS.md", "<permissions",
    "<turn_aborted>", "<user_shell_command>", "<subagent_notification", "<image",
)
_SLASH_RE = re.compile(r"<command-name>\s*(/[\w:-]+)\s*</command-name>")
_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _summarize_agent(tools: dict[str, int], last_text: str) -> str:
    parts = []
    if tools:
        top = sorted(tools.items(), key=lambda kv: -kv[1])[:5]
        parts.append("tools: " + ", ".join(f"{k}x{v}" for k, v in top))
    if last_text:
        t = " ".join(last_text.split())
        parts.append("reply: " + (t[:280] + "…" if len(t) > 280 else t))
    return " | ".join(parts)


def _is_temp_project(dirname: str) -> bool:
    low = dirname.lower()
    return "-temp-" in low or "appdata-local-temp" in low or "agent-coach-judge" in low


# ---------------------------------------------------------------- Claude Code

def claude_root() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"


def _claude_human_text(d: dict) -> tuple[str, int] | None:
    """Return (text, image_count) when this record is a prompt a human typed."""
    if d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta"):
        return None
    origin = d.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return None
    content = (d.get("message") or {}).get("content")
    images = 0
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        if any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            return None
        texts = []
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                texts.append(c.get("text", ""))
            elif c.get("type") == "image":
                images += 1
        text = "\n".join(texts)
    else:
        return None
    return text, images


def parse_claude_file(path: str, include_sdk: bool = False) -> Session | None:
    project = Path(path).parent.name
    turns: list[Turn] = []
    tools: dict[str, int] = {}
    last_text = ""
    first_ts = last_ts = ""
    sid = Path(path).stem
    saw_human = saw_script = False

    def flush():
        nonlocal tools, last_text
        if turns:
            turns[-1].agent_after = _summarize_agent(tools, last_text)
        tools, last_text = {}, ""

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = d.get("timestamp") or ""
            if d.get("type") == "user" and not d.get("isSidechain"):
                origin_human = isinstance(d.get("origin"), dict) and d["origin"].get("kind") == "human"
                if origin_human or d.get("turnOrigin") == "human":
                    saw_human = True
                elif d.get("entrypoint") == "sdk-cli" or d.get("turnOrigin") == "sdk":
                    saw_script = True
                # peer messages, task notifications, scripted prompts: not typed by a person
                if d.get("turnOrigin") not in (None, "human") and not origin_human and not include_sdk:
                    continue
            if d.get("type") == "assistant" and not d.get("isSidechain"):
                for c in (d.get("message") or {}).get("content") or []:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "tool_use":
                        n = c.get("name", "?")
                        tools[n] = tools.get(n, 0) + 1
                    elif c.get("type") == "text" and c.get("text", "").strip():
                        last_text = c["text"]
                continue
            got = _claude_human_text(d)
            if not got:
                continue
            text, images = got
            slash = ""
            m = _SLASH_RE.search(text)
            if m:
                slash = m.group(1)
                a = _ARGS_RE.search(text)
                text = (slash + " " + (a.group(1).strip() if a else "")).strip()
            elif text.lstrip().startswith(_NOISE_PREFIXES):
                continue
            text = text.strip()
            if not text and not images:
                continue
            if turns and turns[-1].text == text:   # resumed sessions repeat the prompt
                continue
            flush()
            turns.append(Turn(index=len(turns) + 1, text=text, ts=ts, images=images, slash=slash))
            first_ts = first_ts or ts
            last_ts = ts or last_ts
    flush()
    scripted = saw_script and not saw_human   # `claude -p` or an app driving the SDK
    if (scripted and not include_sdk) or not turns:
        return None
    return Session("claude", sid, project, path, first_ts, last_ts or first_ts, turns)


def iter_claude(include_sdk: bool = False) -> Iterator[Session]:
    root = claude_root()
    for path in glob.glob(str(root / "*" / "*.jsonl")):
        if _is_temp_project(Path(path).parent.name):
            continue
        s = parse_claude_file(path, include_sdk)
        if s:
            yield s


# ---------------------------------------------------------------- Codex CLI

def codex_root() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def parse_codex_file(path: str, include_sdk: bool = False) -> Session | None:
    turns: list[Turn] = []
    tools: dict[str, int] = {}
    last_text = ""
    sid, project, first_ts, last_ts = Path(path).stem, "", "", ""
    from_items: list[tuple[str, str, int]] = []
    from_events: list[tuple[str, str, int]] = []
    order: list[tuple] = []   # interleaving of user turns and agent activity

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = d.get("timestamp") or ""
            p = d.get("payload") or {}
            t, pt = d.get("type"), p.get("type")
            if t == "session_meta":
                sid = p.get("id") or sid
                cwd = p.get("cwd") or ""
                project = Path(cwd).name if cwd else ""
                # `codex exec`, or another program driving Codex through the app-server
                # (default originator "codex_cli_rs"); the TUI/IDE set their own originator
                scripted = p.get("source") == "exec" or p.get("originator") == "codex_cli_rs" \
                    or p.get("thread_source") not in (None, "user")
                if scripted and not include_sdk:
                    return None
                if _is_temp_project(cwd.replace("\\", "-").replace("/", "-")):
                    return None
            elif t == "response_item" and pt == "message" and p.get("role") == "user":
                texts, images = [], 0
                for c in p.get("content") or []:
                    if c.get("type") in ("input_text", "text"):
                        texts.append(c.get("text", ""))
                    elif c.get("type") in ("input_image", "image"):
                        images += 1
                text = "\n".join(texts).strip()
                if text.startswith(_NOISE_PREFIXES):
                    continue
                order.append(("user", text, ts, images))
            elif t == "event_msg" and pt == "user_message":
                from_events.append((p.get("message", "").strip(), ts, len(p.get("images") or [])))
            elif t == "response_item" and pt in ("function_call", "custom_tool_call", "local_shell_call"):
                order.append(("tool", p.get("name") or pt))
            elif t == "response_item" and pt == "message" and p.get("role") == "assistant":
                txt = " ".join(c.get("text", "") for c in p.get("content") or [] if isinstance(c, dict))
                if txt.strip():
                    order.append(("say", txt))

    has_items = any(o[0] == "user" for o in order)
    if not has_items:   # older rollouts only log user prompts as events
        order = [("user", txt, ts, im) for txt, ts, im in from_events] + [o for o in order if o[0] != "user"]

    def flush():
        nonlocal tools, last_text
        if turns:
            turns[-1].agent_after = _summarize_agent(tools, last_text)
        tools, last_text = {}, ""

    for o in order:
        if o[0] == "user":
            _, text, ts, images = o
            if not text and not images:
                continue
            flush()
            slash = text.split()[0] if text.startswith("/") and text.split() else ""
            turns.append(Turn(index=len(turns) + 1, text=text, ts=ts, images=images, slash=slash))
            first_ts = first_ts or ts
            last_ts = ts or last_ts
        elif o[0] == "tool":
            tools[o[1]] = tools.get(o[1], 0) + 1
        elif o[0] == "say":
            last_text = o[1]
    flush()
    if not turns:
        return None
    return Session("codex", sid, project, path, first_ts, last_ts or first_ts, turns)


def iter_codex(include_sdk: bool = False) -> Iterator[Session]:
    root = codex_root()
    paths = glob.glob(str(root / "sessions" / "**" / "*.jsonl"), recursive=True)
    paths += glob.glob(str(root / "archived_sessions" / "*.jsonl"))
    seen = set()
    for path in paths:
        s = parse_codex_file(path, include_sdk)
        if s and s.id not in seen:
            seen.add(s.id)
            yield s


# ---------------------------------------------------------------- selection

def collect(sources: Iterable[str], since: datetime | None = None,
            include_sdk: bool = False, min_chars: int = 15) -> list[Session]:
    out: list[Session] = []
    for src in sources:
        it = iter_claude(include_sdk) if src == "claude" else iter_codex(include_sdk)
        for s in it:
            end = _parse_ts(s.ended)
            if since and (end is None or end < since):
                continue
            typed = sum(len(t.text) for t in s.turns if not t.slash)
            if typed < min_chars:
                continue
            out.append(s)
    if not include_sdk:
        # the same opening prompt in 3+ sessions is a template a script sent, not a person typing
        firsts: dict[str, int] = {}
        for s in out:
            k = s.turns[0].text[:200]
            firsts[k] = firsts.get(k, 0) + 1
        out = [s for s in out if firsts[s.turns[0].text[:200]] < 3]
    out.sort(key=lambda s: s.ended, reverse=True)
    return out


def pick_sample(sessions: list[Session], limit: int) -> list[Session]:
    """Spread the sample over the whole window, preferring sessions with more turns."""
    if len(sessions) <= limit:
        return sessions
    # interleaved buckets each span the window; take the richest session from each
    buckets = [sessions[i::limit] for i in range(limit)]
    picked = []
    for b in buckets:
        b = sorted(b, key=lambda s: -min(len(s.turns), 30))
        picked.append(b[0])
    picked.sort(key=lambda s: s.ended, reverse=True)
    return picked


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
