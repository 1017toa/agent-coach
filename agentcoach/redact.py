"""Mask secrets and contact details before anything leaves the parser.

Built-in patterns cover keys, tokens, emails, phone/ID numbers and Korean street
addresses. Names can't be detected reliably, so list your own (name, romanized
name, company, address fragments) one per line in ~/.agent-coach/redact.txt.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

_PATTERNS = [
    (re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{16,}"), "[API_KEY]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "[GITHUB_TOKEN]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[AWS_KEY]"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"), "[SLACK_TOKEN]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[JWT]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b\d{6}[- ]?[1-4]\d{6}\b"), "[주민번호]"),
    (re.compile(r"\b(?:\d{4}[- ]){3}\d{4}\b"), "[카드번호]"),
    (re.compile(r"01[016789][-. ]?\d{3,4}[-. ]?\d{4}"), "[전화번호]"),
    # Korean road-name address, optionally followed by building/unit ("행복로 12, 101동 202호")
    (re.compile(r"[가-힣0-9]{1,20}(?:로|길)\s?\d{1,4}(?:-\d{1,4})?(?![0-9가-힣])(?:\s*,?\s*\d{1,4}동)?(?:\s*\d{1,5}호)?"), "[주소]"),
    (re.compile(r"\b\d{1,4}동\s?\d{1,5}호\b"), "[주소]"),
    (re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key|비밀번호|비번)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
]


def _custom_file() -> Path:
    return Path(os.environ.get("AGENT_COACH_HOME", Path.home() / ".agent-coach")) / "redact.txt"


@lru_cache(maxsize=1)
def _custom_terms() -> tuple[str, ...]:
    try:
        lines = _custom_file().read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    terms = {ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")}
    return tuple(sorted(terms, key=len, reverse=True))


def redact(text: str) -> str:
    if not text:
        return text
    for term in _custom_terms():
        text = re.sub(re.escape(term), "[개인정보]", text, flags=re.I)
    for rx, repl in _PATTERNS:
        text = rx.sub(repl, text)
    return text
