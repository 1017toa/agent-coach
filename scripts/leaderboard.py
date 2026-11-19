"""Build the public leaderboard from '[rank]' issues (run by .github/workflows/leaderboard.yml).

Each submission is a GitHub issue opened by `agent-coach rank --submit`. The issue author's GitHub
login is the identity, so nobody can post under someone else's account; the nickname is for display.
Scores are self-reported (grading runs on each person's machine), and the page says so.

    GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python scripts/leaderboard.py [--issue N]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "leaderboard"
API = "https://api.github.com"
MIN_CONVERSATIONS = 3
WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")


def gh(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def rank_issues(repo: str) -> list[dict]:
    out, page = [], 1
    while True:
        batch = gh("GET", f"/repos/{repo}/issues?state=all&per_page=100&page={page}&sort=created&direction=asc")
        if not batch:
            return out
        out += [i for i in batch if "pull_request" not in i and (i.get("title") or "").startswith("[rank]")]
        page += 1


def iso_week(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def parse(issue: dict) -> tuple[dict | None, str]:
    """Return (entry, "") or (None, reason)."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", issue.get("body") or "", re.S)
    if not m:
        return None, "no JSON block found"
    try:
        p = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return None, f"JSON could not be read ({e.msg})"
    if p.get("tool") != "agent-coach" or p.get("schema") != 1:
        return None, "not an agent-coach submission (schema 1)"
    week = str(p.get("week", ""))
    if not WEEK_RE.match(week):
        return None, "week must look like 2026-W47"
    created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    this_week = iso_week(created)
    prev_week = iso_week(created - timedelta(days=7))
    if week not in (this_week, prev_week):
        return None, f"week {week} is too old; submit for {this_week} or {prev_week}"
    try:
        n = int(p["conversations"])
        q = float(p["quality"])
        b = float(p["bonus"])
        s = float(p["score"])
    except (KeyError, TypeError, ValueError):
        return None, "conversations, quality, bonus and score are required numbers"
    if n < MIN_CONVERSATIONS:
        return None, f"at least {MIN_CONVERSATIONS} graded conversations are needed"
    if not (0 <= q <= 100 and 1.0 <= b <= 1.3 and abs(q * b - s) < 0.6):
        return None, "numbers are out of range or don't add up (score = quality x bonus)"
    habits = {k: v for k, v in (p.get("habits") or {}).items()
              if isinstance(k, str) and (v is None or (isinstance(v, (int, float)) and 0 <= v <= 100))}
    imp = p.get("improvement")
    imp = float(imp) if isinstance(imp, (int, float)) and -100 <= imp <= 100 else None
    nick = re.sub(r"[\x00-\x1f<>]", "", str(p.get("nickname") or ""))[:32].strip() or issue["user"]["login"]
    league = re.sub(r"[\x00-\x1f<>]", "", str(p.get("league") or ""))[:32].strip()
    return {"login": issue["user"]["login"], "nickname": nick, "league": league, "week": week,
            "conversations": n, "quality": round(q, 1), "bonus": round(b, 3), "score": round(s, 1),
            "improvement": imp, "habits": habits, "sources": [x for x in p.get("sources", []) if x in ("claude", "codex")],
            "issue": issue["number"], "submitted": issue["created_at"]}, ""


def build(entries: list[dict]) -> dict:
    latest: dict[tuple[str, str], dict] = {}
    for e in sorted(entries, key=lambda e: e["submitted"]):
        latest[(e["login"].lower(), e["week"])] = e     # one entry per person per week; newest wins
    weeks: dict[str, list[dict]] = {}
    for e in latest.values():
        weeks.setdefault(e["week"], []).append(e)
    for w in weeks.values():
        w.sort(key=lambda e: (-e["score"], -e["quality"], e["submitted"]))
    return {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "weeks": dict(sorted(weeks.items(), reverse=True))}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>agent-coach leaderboard</title>
<meta name="description" content="Weekly leaderboard of prompting scores for Claude Code and Codex users, graded by agent-coach.">
<style>
:root{--bg:#f6f6f8;--fg:#1d1d22;--muted:#6b6b76;--card:#fff;--line:#e4e4ea;--acc:#3b5bdb;--gold:#e8a800}
@media (prefers-color-scheme:dark){:root{--bg:#141418;--fg:#ececf1;--muted:#9a9aa6;--card:#1d1d23;--line:#2c2c35;--acc:#7c93ff}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 60px}h1{margin:0 0 4px;font-size:28px}p{color:var(--muted);margin:4px 0 16px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}select,button{font:inherit;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;font-variant-numeric:tabular-nums}th{color:var(--muted);font-weight:600;font-size:13px}
td.n{text-align:right}tr:last-child td{border-bottom:0}.r1{color:var(--gold);font-weight:800}.chip{font-size:12px;color:var(--muted)}
a{color:var(--acc)}.empty{padding:30px;text-align:center;color:var(--muted)}
@media (max-width:640px){.hide{display:none}}
</style></head><body><main>
<h1>agent-coach leaderboard</h1>
<p>Weekly prompting scores for Claude Code and Codex. Score = quality (mean grade of LLM-judged conversations) × a small activity bonus (up to ×1.3). Scores are self-reported: grading runs on each person's own machine. <a href="https://github.com/1017toa/agent-coach#weekly-ranking">How to join</a></p>
<div class="bar"><select id="week"></select><select id="league"></select>
<button id="t-score" class="on">Top score</button><button id="t-imp">Most improved</button></div>
<div id="board"></div>
<p class="chip" id="upd"></p>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const W = Object.keys(D.weeks), $ = id => document.getElementById(id);
let mode = "score";
$("week").innerHTML = W.map(w => `<option>${w}</option>`).join("") || "<option>-</option>";
function leagues(){ const s = new Set((D.weeks[$("week").value] || []).map(e => e.league).filter(Boolean));
  $("league").innerHTML = `<option value="">All leagues</option>` + [...s].sort().map(l => `<option>${esc(l)}</option>`).join(""); }
function draw(){
  let rows = (D.weeks[$("week").value] || []).filter(e => !$("league").value || e.league === $("league").value);
  if (mode === "imp") rows = rows.filter(e => e.improvement != null).sort((a, b) => b.improvement - a.improvement);
  if (!rows.length) { $("board").innerHTML = `<div class="empty">No submissions yet for this view.</div>`; return; }
  $("board").innerHTML = `<table><tr><th>#</th><th>Name</th><th class="n">${mode === "imp" ? "Change" : "Score"}</th><th class="n hide">Quality</th><th class="n hide">Convos</th><th class="hide">League</th></tr>` +
    rows.map((e, i) => `<tr><td class="${i ? "" : "r1"}">${i + 1}</td><td>${esc(e.nickname)} <span class="chip">@${esc(e.login)}</span></td>
    <td class="n"><b>${mode === "imp" ? (e.improvement >= 0 ? "+" : "") + e.improvement : e.score}</b></td><td class="n hide">${e.quality}</td>
    <td class="n hide">${e.conversations}</td><td class="hide chip">${esc(e.league)}</td></tr>`).join("") + `</table>`;
}
$("week").onchange = () => { leagues(); draw(); }; $("league").onchange = draw;
$("t-score").onclick = () => { mode = "score"; $("t-score").classList.add("on"); $("t-imp").classList.remove("on"); draw(); };
$("t-imp").onclick = () => { mode = "imp"; $("t-imp").classList.add("on"); $("t-score").classList.remove("on"); draw(); };
$("upd").textContent = "Updated " + D.updated;
leagues(); draw();
</script></body></html>"""


def write(board: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.dumps(board, ensure_ascii=False).replace("</", "<\\/")
    (OUT / "index.html").write_text(PAGE.replace("__DATA__", data), encoding="utf-8")
    (OUT / "data.json").write_text(json.dumps(board, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", type=int, help="issue that triggered the run; gets a comment and is closed")
    a = ap.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    entries, verdicts = [], {}
    for issue in rank_issues(repo):
        e, why = parse(issue)
        verdicts[issue["number"]] = (e, why)
        if e:
            entries.append(e)
    board = build(entries)
    write(board)
    if a.issue and a.issue in verdicts:
        e, why = verdicts[a.issue]
        if e:
            rows = board["weeks"].get(e["week"], [])
            pos = next((i + 1 for i, x in enumerate(rows) if x["issue"] == e["issue"]), None)
            msg = (f"Recorded for {e['week']}: score **{e['score']}** (quality {e['quality']} x {e['bonus']}). "
                   f"Current rank: **#{pos} of {len(rows)}**. "
                   f"Leaderboard: https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/leaderboard/")
            reason = "completed"
        else:
            msg = f"This submission couldn't be recorded: {why}. Run `agent-coach rank --submit` again to open a fresh one."
            reason = "not_planned"
        gh("POST", f"/repos/{repo}/issues/{a.issue}/comments", {"body": html.unescape(msg)})
        gh("PATCH", f"/repos/{repo}/issues/{a.issue}", {"state": "closed", "state_reason": reason})
    print(f"{len(entries)} valid submissions, {len(board['weeks'])} weeks")


if __name__ == "__main__":
    sys.exit(main())
