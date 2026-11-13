import json
import re
import unittest
from pathlib import Path

from agentcoach import __version__

ROOT = Path(__file__).resolve().parents[1]


class Release(unittest.TestCase):
    def test_versions_match(self):
        py = re.search(r'^version = "(.+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
        claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
        codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertEqual({py, claude, codex}, {__version__})

    def test_skill_frontmatter(self):
        text = (ROOT / "skills/coach/SKILL.md").read_text(encoding="utf-8")
        head = text.split("---")[1]
        self.assertIn("name: coach", head)
        self.assertIn("description:", head)

    def test_summary_runs(self):
        import io
        import os
        import tempfile
        from contextlib import redirect_stdout
        from agentcoach.cli import main
        from agentcoach.rubric import load_rubric
        from agentcoach.store import build_run, save_run
        with tempfile.TemporaryDirectory() as home:
            os.environ["AGENT_COACH_HOME"] = home
            try:
                rubric = load_rubric(lang="en")
                run = build_run([], {}, rubric, None, "heuristic")
                run["lang"] = "en"
                save_run(run)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    main(["summary"])
                self.assertIn("agent-coach", buf.getvalue())
            finally:
                del os.environ["AGENT_COACH_HOME"]
