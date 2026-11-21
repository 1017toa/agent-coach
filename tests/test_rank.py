import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agentcoach.card import render_card
from agentcoach.rank import activity_bonus, issue_url, payload, weekly
from agentcoach.rubric import load_rubric

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("leaderboard", ROOT / "scripts" / "leaderboard.py")
lb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lb)

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def sess(i, days_ago, score, judge="claude:sonnet", project="secret-project"):
    t = (NOW - timedelta(days=days_ago)).isoformat()
    return {"id": f"s{i}", "source": "claude", "project": project, "started": t, "ended": t, "judge": judge,
            "dimensions": {"done_criteria": {"score": score}, "constraints": {"score": score}}}


class Weekly(unittest.TestCase):
    def test_bonus_curve(self):
        self.assertEqual(activity_bonus(1), 1.0)
        self.assertAlmostEqual(activity_bonus(5), 1.161, places=2)
        self.assertEqual(activity_bonus(20), 1.3)
        self.assertEqual(activity_bonus(200), 1.3)

    def test_weekly_counts_only_llm_graded_recent_sessions(self):
        rubric = load_rubric(lang="en")
        runs = [{"created": NOW.isoformat(), "sessions": [
            sess(1, 1, 2), sess(2, 2, 1), sess(3, 3, 2),
            sess(4, 2, 0, judge="heuristic"),       # offline score: excluded
            sess(5, 10, 0),                          # last week: excluded from this window
        ]}]
        w = weekly(runs, rubric, end=NOW)
        self.assertEqual(w["conversations"], 3)
        self.assertAlmostEqual(w["quality"], (100 + 50 + 100) / 3, places=1)
        self.assertTrue(w["eligible"])
        self.assertEqual(w["week"], "2026-W47")
        p = payload(w, "tester")
        self.assertNotIn("secret-project", json.dumps(p))
        self.assertIn("issues/new?title=", issue_url("o/r", p))

    def test_tiers(self):
        from agentcoach.rank import tier_of
        self.assertEqual(tier_of(0)["id"], "iron")
        self.assertEqual(tier_of(59.9)["id"], "silver")
        self.assertEqual(tier_of(60)["id"], "gold")
        g = tier_of(66)
        self.assertEqual((g["next"], g["gap"]), ("platinum", 9.0))
        self.assertAlmostEqual(g["progress"], 0.4)
        m = tier_of(120)
        self.assertEqual((m["id"], m["next"], m["progress"]), ("master", None, 1.0))
        self.assertEqual(tier_of(None)["id"], "iron")

    def test_card_escapes_nickname(self):
        rubric = load_rubric(lang="ko")
        w = weekly([{"created": NOW.isoformat(), "sessions": [sess(1, 1, 2)]}], rubric, end=NOW)
        out = render_card(payload(w, "<b>x</b>"), rubric, "ko")
        self.assertNotIn("<b>x</b>", out)
        self.assertIn("대화 3개 이상", out)


class Leaderboard(unittest.TestCase):
    def issue(self, n, login, p, created="2026-11-19T10:00:00Z"):
        return {"number": n, "user": {"login": login}, "created_at": created, "title": "[rank] x",
                "body": "```json\n" + json.dumps(p) + "\n```"}

    def good(self, **kw):
        p = {"schema": 1, "tool": "agent-coach", "week": "2026-W47", "nickname": "A", "league": "",
             "conversations": 8, "quality": 60.0, "bonus": 1.2, "score": 72.0, "improvement": 3.0,
             "habits": {"done_criteria": 40}, "sources": ["claude"]}
        p.update(kw)
        return p

    def test_parse_validates(self):
        e, why = lb.parse(self.issue(1, "alice", self.good()))
        self.assertEqual(why, "")
        self.assertEqual(e["login"], "alice")
        for bad in (dict(conversations=2), dict(score=99.0), dict(bonus=2.0), dict(week="2026-W30"), dict(tool="x")):
            e, why = lb.parse(self.issue(2, "bob", self.good(**bad)))
            self.assertIsNone(e, bad)
            self.assertTrue(why)

    def test_one_entry_per_person_per_week(self):
        a1, _ = lb.parse(self.issue(1, "alice", self.good(quality=50.0, score=60.0), "2026-11-18T10:00:00Z"))
        a2, _ = lb.parse(self.issue(2, "Alice", self.good(quality=70.0, score=84.0), "2026-11-19T10:00:00Z"))
        b, _ = lb.parse(self.issue(3, "bob", self.good(quality=65.0, score=78.0)))
        board = lb.build([a1, a2, b])
        rows = board["weeks"]["2026-W47"]
        self.assertEqual([r["issue"] for r in rows], [2, 3])
        self.assertEqual([r["tier"] for r in rows], ["platinum", "platinum"])   # 84 and 78
        self.assertEqual(board["tiers"][0]["id"], "iron")


if __name__ == "__main__":
    unittest.main()
