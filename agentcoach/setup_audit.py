"""Check the setup the agent runs in, not just the prompts.

As the agent takes over steering and approving, guarantees move into the harness
(deny rules, hooks, CI) and the environment (sandbox). This module reads local
config files only, makes no network or model calls, and never prints file
contents beyond the matched rule or word.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PASS, WARN, FAIL, NA = "pass", "warn", "fail", "na"
WEIGHT = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Check:
    id: str
    area: str            # safety | verification | instructions
    severity: str        # high | medium | low
    status: str          # pass | warn | fail | na
    title: dict
    detail: dict = field(default_factory=dict)
    fix: dict = field(default_factory=dict)
    source: str = ""     # rubric source id
    section: str = ""


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _toml_value(text: str, key: str) -> str | None:
    """Top-level `key = "value"` from a TOML file (stdlib tomllib needs 3.11)."""
    for line in text.splitlines():
        if line.strip().startswith("["):
            break  # only the top-level table
        m = re.match(rf'\s*{re.escape(key)}\s*=\s*["\']?([^"\'#\s]+)', line)
        if m:
            return m.group(1)
    return None


@dataclass
class Setup:
    home: Path
    project: Path
    settings: list[tuple[Path, dict]]
    memory_files: list[Path]
    codex_config: str
    is_repo: bool

    @classmethod
    def load(cls, home: Path | None = None, project: Path | None = None) -> "Setup":
        home = Path(home or Path.home())
        project = Path(project or Path.cwd())
        cands = [home / ".claude" / "settings.json", project / ".claude" / "settings.json",
                 project / ".claude" / "settings.local.json"]
        settings = [(p, _load_json(p)) for p in cands if p.exists()]
        mem = [p for p in (home / ".claude" / "CLAUDE.md", project / "CLAUDE.md", project / ".claude" / "CLAUDE.md",
                           project / "CLAUDE.local.md", home / ".codex" / "AGENTS.md", project / "AGENTS.md")
               if p.exists() and p.is_file()]
        codex = _read(home / ".codex" / "config.toml")
        return cls(home, project, settings, mem, codex, (project / ".git").exists())

    # merged views -------------------------------------------------------
    def perm(self, key: str) -> list:
        out = []
        for _, s in self.settings:
            out += (s.get("permissions") or {}).get(key) or []
        return out

    def default_mode(self) -> str | None:
        mode = None
        for _, s in self.settings:  # later files (project, local) override user
            mode = (s.get("permissions") or {}).get("defaultMode") or mode
        return mode

    def hooks(self) -> dict[str, list]:
        out: dict[str, list] = {}
        for _, s in self.settings:
            for ev, groups in (s.get("hooks") or {}).items():
                out.setdefault(ev, []).extend(groups or [])
        return out

    def sandbox_on(self) -> bool:
        return any(((s.get("sandbox") or {}).get("enabled") is True) for _, s in self.settings)


def _hook_commands(groups: list) -> list[tuple[str, str]]:
    """(matcher, command) pairs from a hooks event list."""
    out = []
    for g in groups:
        for h in g.get("hooks") or []:
            if h.get("type", "command") == "command" and h.get("command"):
                out.append((g.get("matcher", ""), h["command"]))
    return out


SECRET_RX = re.compile(r"Read\([^)]*\.env", re.I)
SSH_RX = re.compile(r"Read\([^)]*\.ssh", re.I)
SHOUT_RX = re.compile(r"\b(IMPORTANT|CRITICAL|MUST|NEVER|ALWAYS)\b|!!+|절대|반드시|무조건")
DISCOVERABLE_RX = re.compile(r"^#+\s*(tech(nology)?\s*stack|project\s*structure|directory\s*(structure|layout)|folder\s*structure|"
                             r"기술\s*스택|폴더\s*구조|디렉터리\s*구조|프로젝트\s*구조)", re.I | re.M)
TEST_RX = re.compile(r"\b(test|pytest|jest|vitest|unittest|go test|cargo test|npm (run )?test|lint|tsc|build|ruff|eslint)\b", re.I)


def audit(setup: Setup) -> list[Check]:
    s, checks = setup, []
    deny = [str(x) for x in s.perm("deny")]
    mode = s.default_mode()
    hooks = s.hooks()

    # --- safety: things that must never happen are rules, not hopes -------------
    checks.append(Check(
        "deny_secrets", "safety", "high", PASS if any(SECRET_RX.search(d) for d in deny) else FAIL,
        {"en": "Deny rule keeps .env files out of reach", "ko": ".env 파일 읽기를 막는 deny 규칙"},
        {"en": "Auto mode allows reading .env by default; a deny rule is checked before the classifier.",
         "ko": "auto mode는 기본적으로 .env 읽기를 허용합니다. deny 규칙은 분류기보다 먼저 적용됩니다."},
        {"en": 'Add to ~/.claude/settings.json: "permissions": {"deny": ["Read(./.env)", "Read(./.env.*)"]}',
         "ko": '~/.claude/settings.json 에 추가: "permissions": {"deny": ["Read(./.env)", "Read(./.env.*)"]}'},
        "claude-permission-modes", "How the classifier evaluates actions"))
    checks.append(Check(
        "deny_ssh", "safety", "medium", PASS if any(SSH_RX.search(d) for d in deny) else WARN,
        {"en": "Deny rule for SSH keys", "ko": "SSH 키 읽기를 막는 deny 규칙"},
        {"en": "Anything Claude reads lands in the transcript and can't be taken back.",
         "ko": "읽은 내용은 대화 기록에 남아 되돌릴 수 없습니다."},
        {"en": 'Add "Read(~/.ssh/**)" to permissions.deny', "ko": 'permissions.deny 에 "Read(~/.ssh/**)" 추가'},
        "claude-permission-modes", "How the classifier evaluates actions"))
    checks.append(Check(
        "no_bypass", "safety", "high", FAIL if mode == "bypassPermissions" else PASS,
        {"en": "Not running with every permission check skipped", "ko": "권한 확인을 통째로 끄지 않음"},
        {"en": f"permissions.defaultMode = {mode or 'default'}", "ko": f"permissions.defaultMode = {mode or '기본값'}"},
        {"en": "Use auto mode instead of bypassPermissions; it still blocks commands it isn't sure are safe.",
         "ko": "bypassPermissions 대신 auto mode를 쓰세요. 안전한지 확실하지 않은 명령은 막아 줍니다."},
        "claude-permission-modes", "Eliminate permission prompts with auto mode"))
    checks.append(Check(
        "sandbox", "safety", "medium", PASS if s.sandbox_on() else (NA if sys.platform == "win32" else WARN),
        {"en": "Sandbox limits what commands can reach", "ko": "샌드박스로 명령이 닿는 범위 제한"},
        {"en": "Not available on native Windows (macOS, Linux, WSL2 only)." if sys.platform == "win32" and not s.sandbox_on()
               else "Permissions decide whether `npm test` runs, not what its dependencies open once running.",
         "ko": "Windows에서는 쓸 수 없습니다 (macOS·Linux·WSL2 전용)." if sys.platform == "win32" and not s.sandbox_on()
               else "권한은 npm test 실행 여부만 정하고, 실행 중 의존성이 무엇을 여는지는 막지 못합니다."},
        {"en": 'Turn on the sandbox: "sandbox": {"enabled": true} (or /sandbox; macOS, Linux, WSL2). On native Windows, run long tasks in a cloud session.',
         "ko": '샌드박스 켜기: "sandbox": {"enabled": true} (또는 /sandbox, macOS·Linux·WSL2). Windows에서는 긴 작업을 클라우드 세션에서 돌리세요.'},
        "claude-sandboxing", "What the sandbox restricts"))
    if s.codex_config:
        sm = _toml_value(s.codex_config, "sandbox_mode")
        ap = _toml_value(s.codex_config, "approval_policy")
        risky = sm == "danger-full-access"
        checks.append(Check(
            "codex_sandbox", "safety", "high", FAIL if risky else PASS,
            {"en": "Codex keeps its sandbox on", "ko": "Codex 샌드박스 유지"},
            {"en": f"sandbox_mode = {sm or 'default'}, approval_policy = {ap or 'default'}",
             "ko": f"sandbox_mode = {sm or '기본값'}, approval_policy = {ap or '기본값'}"},
            {"en": 'Use sandbox_mode = "workspace-write" in ~/.codex/config.toml',
             "ko": '~/.codex/config.toml 에서 sandbox_mode = "workspace-write" 사용'},
            "codex-best-practices", "Configure Codex for your real environment"))

    # --- verification: checks that must run go in hooks and CI -----------------
    finish = [c for ev in ("Stop", "SubagentStop", "TaskCompleted") for c in _hook_commands(hooks.get(ev, []))]
    checks.append(Check(
        "hook_finish_tests", "verification", "medium",
        PASS if any(TEST_RX.search(c) for _, c in finish) else WARN,
        {"en": "Tests run automatically before Claude can finish", "ko": "끝내기 전에 테스트가 자동으로 돌아감"},
        {"en": f"{len(finish)} Stop/TaskCompleted hook(s) found", "ko": f"Stop/TaskCompleted 훅 {len(finish)}개"},
        {"en": "Add a Stop (or TaskCompleted) hook that runs your tests; prompting alone isn't a guarantee.",
         "ko": "테스트를 돌리는 Stop(또는 TaskCompleted) 훅을 추가하세요. 프롬프트만으로는 보장되지 않습니다."},
        "claude-hooks", "TaskCompleted / Stop"))
    edits = [c for m, c in _hook_commands(hooks.get("PostToolUse", [])) if re.search(r"Edit|Write|\*|^$", m or "")]
    checks.append(Check(
        "hook_edit_lint", "verification", "low", PASS if edits else WARN,
        {"en": "Linter or formatter runs after each edit", "ko": "파일을 고칠 때마다 린터·포매터 실행"},
        {"en": f"{len(edits)} PostToolUse hook(s) on edits", "ko": f"편집 뒤 PostToolUse 훅 {len(edits)}개"},
        {"en": "Add a PostToolUse hook with matcher Edit|Write that runs your linter.",
         "ko": "matcher 가 Edit|Write 인 PostToolUse 훅으로 린터를 돌리세요."},
        "claude-hooks", "PostToolUse"))
    scripts, blocking = [], 0
    for ev, groups in hooks.items():
        blocking += sum(1 for g in groups for h in (g.get("hooks") or []) if h.get("onFailure") == "block")
        for _, cmd in _hook_commands(groups):
            for tok in re.findall(r"[\w./\\~$-]+\.(?:sh|py|js|mjs|ps1)", cmd):
                p = Path(tok.replace("$CLAUDE_PROJECT_DIR", str(s.project)).replace("~", str(s.home)))
                if not p.is_absolute():
                    p = s.project / p
                if p.exists():
                    scripts.append(p)
    exit1 = [p for p in scripts if re.search(r"\bexit\s*\(?\s*1\b|sys\.exit\(\s*1\s*\)|process\.exit\(\s*1\s*\)", _read(p))
             and not re.search(r"\bexit\s*\(?\s*2\b|sys\.exit\(\s*2\s*\)|process\.exit\(\s*2\s*\)", _read(p))]
    checks.append(Check(
        "hook_exit_code", "verification", "medium", NA if not scripts else (WARN if exit1 and not blocking else PASS),
        {"en": "Failing hooks exit with code 2", "ko": "실패한 훅이 종료 코드 2로 끝남"},
        {"en": f"{len(exit1)} of {len(scripts)} hook script(s) only ever exit 1" if scripts else "no hook scripts to check",
         "ko": f"훅 스크립트 {len(scripts)}개 중 {len(exit1)}개가 실패 시 1로만 종료" if scripts else "점검할 훅 스크립트 없음"},
        {"en": 'Exit 2 on failure (or set "onFailure": "block") so Claude is sent back to fix it; exit 1 lets the task finish anyway.',
         "ko": '실패하면 2로 끝내야(또는 "onFailure": "block") Claude가 돌아가서 고칩니다. 1이면 그냥 완료 처리됩니다.'},
        "claude-hooks", "Exit code 2 behavior"))
    if s.is_repo:
        wf = list((s.project / ".github" / "workflows").glob("*.y*ml"))
        checks.append(Check(
            "ci", "verification", "medium", PASS if wf else WARN,
            {"en": "CI runs the same checks on every PR", "ko": "모든 PR에 같은 검사를 돌리는 CI"},
            {"en": f"{len(wf)} workflow file(s) in this repo", "ko": f"이 저장소의 워크플로 파일 {len(wf)}개"},
            {"en": "Add a CI workflow that runs tests and lint; with autofix, Claude fixes what fails.",
             "ko": "테스트·린트를 돌리는 CI 를 두세요. autofix 를 켜면 실패를 Claude 가 고칩니다."},
            "claude-web", "Auto-fix pull requests"))

    # --- instructions: only what the model can't see from the code -------------
    if s.memory_files:
        shout, disc, longest = 0, [], 0
        for p in s.memory_files:
            txt = _read(p)
            shout += len(SHOUT_RX.findall(txt))
            longest = max(longest, txt.count("\n") + 1)
            if DISCOVERABLE_RX.search(txt):
                disc.append(p.name)
        checks.append(Check(
            "memory_no_shouting", "instructions", "medium", PASS if shout < 3 else WARN,
            {"en": "CLAUDE.md / AGENTS.md without shouted rules", "ko": "CLAUDE.md·AGENTS.md에 강조어 남발 없음"},
            {"en": f"{shout} IMPORTANT / NEVER / !!! style markers", "ko": f"IMPORTANT·NEVER·!!!·절대 같은 강조 {shout}곳"},
            {"en": "Current models follow plain instructions; shouting makes them overcorrect. State the rule calmly.",
             "ko": "요즘 모델은 평범하게 써도 따릅니다. 강조하면 과하게 반응하니 담담하게 쓰세요."},
            "claude-best-practices", "Troubleshooting: emphasis in instructions"))
        checks.append(Check(
            "memory_only_unseen", "instructions", "low", WARN if disc else PASS,
            {"en": "Memory files hold only what the code can't show", "ko": "코드에서 안 보이는 것만 메모리 파일에"},
            {"en": "Sections Claude can read from the code: " + (", ".join(sorted(set(disc))) or "none"),
             "ko": "코드에서 알 수 있는 섹션: " + (", ".join(sorted(set(disc))) or "없음")},
            {"en": "Drop stack and folder-layout sections; keep things like legacy sources not referenced in code.",
             "ko": "기술 스택·폴더 구조 설명은 빼고, 코드에 드러나지 않는 레거시 같은 것만 남기세요."},
            "claude-memory", "CLAUDE.md vs auto memory"))
        checks.append(Check(
            "memory_short", "instructions", "low", PASS if longest <= 200 else WARN,
            {"en": "Memory files stay short", "ko": "메모리 파일을 짧게 유지"},
            {"en": f"longest file: {longest} lines", "ko": f"가장 긴 파일: {longest}줄"},
            {"en": "Trim it; for each line ask whether removing it would cause a mistake.",
             "ko": "줄마다 '지우면 실수가 생기나?'를 묻고 줄이세요."},
            "claude-best-practices", "Write an effective CLAUDE.md"))
    return checks


def score(checks: list[Check]) -> dict:
    def pct(cs):
        cs = [c for c in cs if c.status != NA]
        if not cs:
            return None
        got = sum(WEIGHT[c.severity] * (1 if c.status == PASS else 0.5 if c.status == WARN else 0) for c in cs)
        return round(100 * got / sum(WEIGHT[c.severity] for c in cs))
    areas = {a: pct([c for c in checks if c.area == a]) for a in ("safety", "verification", "instructions")}
    return {"overall": pct(checks), "areas": areas}


def to_json(setup: Setup, checks: list[Check]) -> dict:
    return {"project": setup.project.name, "files": [str(p) for p, _ in setup.settings] + [str(p) for p in setup.memory_files],
            "score": score(checks), "checks": [asdict(c) for c in checks]}
