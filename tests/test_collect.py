import json
import os
import tempfile
import unittest
from pathlib import Path

from agentcoach.collect import parse_claude_file, parse_codex_file
from agentcoach.heuristics import score_session
from agentcoach.redact import redact
from agentcoach.rubric import load_rubric
from agentcoach.store import build_run


def _write(lines):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for d in lines:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    return path


def claude_user(text, **kw):
    return {"type": "user", "timestamp": "2026-11-10T01:00:00Z", "turnOrigin": "human",
            "origin": {"kind": "human"}, "entrypoint": "claude-desktop",
            "message": {"role": "user", "content": text}, **kw}


class ClaudeParse(unittest.TestCase):
    def test_human_turns_and_agent_summary(self):
        p = _write([
            claude_user("src/auth/login.py 에서 세션 만료 후 로그인 실패해. 고치고 pytest 돌려줘"),
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit"},
                                                          {"type": "text", "text": "고쳤고 테스트 통과했습니다"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
            {"type": "user", "turnOrigin": "task_notification", "message": {"content": "<task-notification>x"}},
            claude_user("<command-name>/clear</command-name><command-args></command-args>"),
            claude_user("아니 다시 해봐"),
        ])
        s = parse_claude_file(p)
        self.assertEqual([t.text for t in s.turns], [
            "src/auth/login.py 에서 세션 만료 후 로그인 실패해. 고치고 pytest 돌려줘", "/clear", "아니 다시 해봐"])
        self.assertIn("Editx1", s.turns[0].agent_after)
        self.assertEqual(s.turns[1].slash, "/clear")

    def test_scripted_session_skipped(self):
        p = _write([{"type": "user", "entrypoint": "sdk-cli", "turnOrigin": "sdk",
                     "message": {"content": "automated prompt"}}])
        self.assertIsNone(parse_claude_file(p))
        self.assertIsNotNone(parse_claude_file(p, include_sdk=True))


class CodexParse(unittest.TestCase):
    def test_rollout(self):
        p = _write([
            {"type": "session_meta", "timestamp": "2026-11-09T03:55:42Z",
             "payload": {"id": "abc", "cwd": "C:\\proj\\demo", "source": "vscode",
                         "originator": "codex-tui", "thread_source": "user"}},
            {"type": "response_item", "timestamp": "2026-11-09T03:55:43Z", "payload": {
                "type": "message", "role": "user", "content": [{"type": "input_text", "text": "<environment_context>..."}]}},
            {"type": "response_item", "timestamp": "2026-11-09T03:55:44Z", "payload": {
                "type": "message", "role": "user", "content": [{"type": "input_text", "text": "README 오타 고쳐줘"}]}},
            {"type": "response_item", "payload": {"type": "function_call", "name": "shell"}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                                                  "content": [{"type": "output_text", "text": "고쳤어요"}]}},
        ])
        s = parse_codex_file(p)
        self.assertEqual(s.project, "demo")
        self.assertEqual([t.text for t in s.turns], ["README 오타 고쳐줘"])
        self.assertIn("shellx1", s.turns[0].agent_after)

    def test_exec_skipped(self):
        p = _write([{"type": "session_meta", "payload": {"id": "x", "cwd": "C:\\a", "source": "exec"}}])
        self.assertIsNone(parse_codex_file(p))
        p = _write([{"type": "session_meta", "payload": {"id": "y", "cwd": "C:\\a", "source": "vscode",
                                                          "originator": "codex_cli_rs"}}])
        self.assertIsNone(parse_codex_file(p))


class Scoring(unittest.TestCase):
    def test_heuristic_and_aggregate(self):
        rubric = load_rubric()
        p = _write([claude_user("src/app.py 버그 고쳐줘. 새 라이브러리 쓰지 말고, 끝나면 pytest 돌려서 통과할 때까지 해줘")])
        s = parse_claude_file(p)
        r = score_session(s, rubric)
        self.assertEqual(r["dimensions"]["done_criteria"]["score"], 2)
        self.assertEqual(r["dimensions"]["constraints"]["score"], 2)
        run = build_run([s], {s.id: r}, rubric, None, "heuristic")
        self.assertEqual(run["dimensions"]["done_criteria"]["score"], 100)
        self.assertEqual(len(run["dimensions"]), len(rubric["dimensions"]))

    def test_new_dimensions(self):
        rubric = load_rubric()
        p = _write([claude_user("지원서 채워서 제출해줘. 최종 제출 직전에는 멈추고 나한테 확인받아"),
                    claude_user("앞으로 탐사는 무조건 x1이야"),
                    claude_user("탐사는 무조건 x1이라니까"),
                    claude_user("무조건 x1으로 해")])
        r = score_session(parse_claude_file(p), rubric)["dimensions"]
        self.assertEqual(r["stop_conditions"]["score"], 2)
        self.assertEqual(r["reusable_guidance"]["score"], 0)
        self.assertIsNone(r["focused_session"]["score"])

    def test_report_renders_old_runs(self):
        from agentcoach.report import render
        rubric = load_rubric()
        old = {"created": "2026-11-01T00:00:00+09:00", "overall": 50, "judge": "x", "session_count": 0,
               "sources": [], "sessions": [], "rubric": {"version": 1},
               "dimensions": {"done_criteria": {"score": 50, "n": 1, "missed": 0}}}
        html_out = render([old], rubric)
        self.assertIn("멈출 지점", html_out)


class Redact(unittest.TestCase):
    def test_masks(self):
        t = redact("key sk-ant-abcdefghijklmnopqrstuv mail a.b@x.com 010-1234-5678")
        self.assertNotIn("sk-ant", t)
        self.assertNotIn("@x.com", t)
        self.assertNotIn("1234-5678", t)


if __name__ == "__main__":
    unittest.main()
