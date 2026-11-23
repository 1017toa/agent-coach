import json
import tempfile
import unittest
from pathlib import Path

from agentcoach.setup_audit import Setup, audit, score, to_json


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class SetupAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home, self.proj = root / "home", root / "proj"
        self.home.mkdir()
        (self.proj / ".git").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_audit(self):
        checks = audit(Setup.load(self.home, self.proj))
        return {c.id: c for c in checks}, score(checks)

    def test_empty_setup_flags_safety_and_verification(self):
        c, sc = self.run_audit()
        self.assertEqual(c["deny_secrets"].status, "fail")
        self.assertEqual(c["hook_finish_tests"].status, "warn")
        self.assertEqual(c["ci"].status, "warn")
        self.assertNotIn("memory_no_shouting", c)  # no memory files to judge
        self.assertLess(sc["overall"], 60)

    def test_good_setup_passes(self):
        script = self.proj / ".claude" / "hooks" / "check.sh"
        write(script, "npm test || exit 2\n")
        write(self.home / ".claude" / "settings.json", json.dumps({
            "permissions": {"deny": ["Read(./.env)", "Read(~/.ssh/**)"], "defaultMode": "auto"},
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "npm test"}]}],
                "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "bash .claude/hooks/check.sh"}]}],
            }}))
        write(self.proj / ".github" / "workflows" / "ci.yml", "on: push\n")
        write(self.proj / "CLAUDE.md", "The billing service still reads from the legacy orders table.\n")
        c, sc = self.run_audit()
        for cid in ("deny_secrets", "deny_ssh", "no_bypass", "hook_finish_tests", "hook_edit_lint",
                    "hook_exit_code", "ci", "memory_no_shouting", "memory_only_unseen"):
            self.assertEqual(c[cid].status, "pass", cid)

    def test_bypass_exit1_and_shouting_are_flagged(self):
        script = self.proj / "lint.py"
        write(script, "import sys\nsys.exit(1)\n")
        write(self.proj / ".claude" / "settings.json", json.dumps({
            "permissions": {"defaultMode": "bypassPermissions"},
            "hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": [{"command": "python lint.py"}]}]}}))
        write(self.proj / "CLAUDE.md", "## Tech stack\nIMPORTANT: NEVER skip tests!!!\nYou MUST lint.\n")
        write(self.home / ".codex" / "config.toml", 'sandbox_mode = "danger-full-access"\n[profiles.x]\nmodel = "y"\n')
        c, _ = self.run_audit()
        self.assertEqual(c["no_bypass"].status, "fail")
        self.assertEqual(c["hook_exit_code"].status, "warn")
        self.assertEqual(c["memory_no_shouting"].status, "warn")
        self.assertEqual(c["memory_only_unseen"].status, "warn")
        self.assertEqual(c["codex_sandbox"].status, "fail")

    def test_json_has_no_file_contents(self):
        write(self.proj / "CLAUDE.md", "secret-token-abc123\n")
        out = json.dumps(to_json(Setup.load(self.home, self.proj), audit(Setup.load(self.home, self.proj))))
        self.assertNotIn("secret-token-abc123", out)


if __name__ == "__main__":
    unittest.main()
