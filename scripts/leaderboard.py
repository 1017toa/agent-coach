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
sys.path.insert(0, str(ROOT))
from agentcoach.rank import TIERS, tier_of  # noqa: E402  (same tier thresholds as the CLI)
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
        for e in w:
            e["tier"] = tier_of(e["score"])["id"]     # from the score, never from the submission
    return {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tiers": [{"id": tid, "min": lo, "en": en, "ko": ko, "from": g[0], "to": g[1], "accent": a}
                      for lo, tid, ko, en, g, a in reversed(TIERS)],
            "weeks": dict(sorted(weeks.items(), reverse=True))}


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>agent-coach leaderboard</title>
<meta name="description" content="Weekly leaderboard and tiers of prompting scores for Claude Code and Codex users, graded by agent-coach.">
<style>
:root{--bg:#f6f6f8;--fg:#1d1d22;--muted:#6b6b76;--card:#fff;--line:#e4e4ea;--acc:#3b5bdb}
@media (prefers-color-scheme:dark){:root{--bg:#0f0f13;--fg:#ececf1;--muted:#9a9aa6;--card:#1a1a20;--line:#2a2a33;--acc:#8a9dff}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif}
main{max-width:960px;margin:0 auto;padding:28px 16px 64px}h1{margin:0 0 4px;font-size:30px;letter-spacing:-.5px}
p{color:var(--muted);margin:4px 0 16px;line-height:1.5}a{color:var(--acc)}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}select,button{font:inherit;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.dist{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--line);margin:8px 0 4px}.dist i{display:block;height:100%;transition:width .8s}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--muted);margin-bottom:14px}.legend b{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.podium{display:grid;grid-template-columns:1fr 1.15fr 1fr;gap:12px;align-items:end;margin:18px 0}
.pod{border-radius:18px;padding:16px 12px;text-align:center;color:#fff;position:relative;overflow:hidden;animation:rise .7s cubic-bezier(.2,1.3,.4,1) both;box-shadow:0 10px 30px #0003}
.pod.p1{padding:24px 12px;animation-delay:.15s}.pod.p2{animation-delay:.3s}.pod.p3{animation-delay:.45s}
.pod .m{font-size:30px}.pod .nm{font-weight:800;font-size:17px;margin-top:4px;word-break:break-all}.pod .sc{font-size:34px;font-weight:900;margin-top:2px}.pod .tr{font-size:12px;opacity:.9}
.pod::after{content:"";position:absolute;top:-50%;left:-60%;width:40%;height:200%;background:linear-gradient(90deg,#fff0,#fff5,#fff0);transform:rotate(18deg);animation:sweep 3.5s ease-in-out 1s infinite}
.pod.p1{outline:3px solid #ffe066;animation:rise .7s cubic-bezier(.2,1.3,.4,1) .15s both,glow 2.4s ease-in-out 1s infinite}
@keyframes rise{from{transform:translateY(30px) scale(.9);opacity:0}}@keyframes sweep{0%{left:-60%}55%,100%{left:130%}}
@keyframes glow{50%{box-shadow:0 0 0 6px #ffe06655,0 10px 40px #ffd43b88}}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;font-variant-numeric:tabular-nums}th{color:var(--muted);font-weight:600;font-size:13px}
td.n{text-align:right}tr:last-child td{border-bottom:0}tr.row{animation:fade .5s ease both}@keyframes fade{from{opacity:0;transform:translateX(-8px)}}
.tier{display:inline-flex;align-items:center;gap:6px;padding:3px 9px 3px 4px;border-radius:999px;color:#fff;font-size:12px;font-weight:700;white-space:nowrap}
.tier .hx{width:18px;height:18px;display:grid;place-items:center;font-size:11px;clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%);background:#fff3}
.tier.master,.tier.diamond{position:relative;overflow:hidden}.tier.master::after,.tier.diamond::after{content:"";position:absolute;inset:0;background:linear-gradient(100deg,#fff0 30%,#fff8 50%,#fff0 70%);transform:translateX(-100%);animation:chip 2.6s ease-in-out infinite}
@keyframes chip{60%,100%{transform:translateX(100%)}}
.chip{font-size:12px;color:var(--muted)}.empty{padding:30px;text-align:center;color:var(--muted);background:var(--card);border-radius:14px}
@media (max-width:640px){.hide{display:none}.podium{gap:8px}.pod .sc{font-size:26px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body><main>
<h1>agent-coach leaderboard</h1>
<p>Weekly prompting scores for Claude Code and Codex. Score = quality (mean grade of LLM-judged conversations) × a small activity bonus (up to ×1.3), and the score sets your tier. Scores are self-reported: grading runs on each person's own machine. <a href="https://github.com/1017toa/agent-coach#weekly-ranking">How to join</a></p>
<div class="bar"><select id="week"></select><select id="league"></select>
<button id="t-score" class="on">Top score</button><button id="t-imp">Most improved</button></div>
<div class="dist" id="dist"></div><div class="legend" id="legend"></div>
<div id="podium"></div>
<div id="board"></div>
<p class="chip" id="upd"></p>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const W = Object.keys(D.weeks), $ = id => document.getElementById(id);
const T = Object.fromEntries((D.tiers || []).map(t => [t.id, t]));
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const badge = id => { const t = T[id] || {en: "?", from: "#888", to: "#555"};
  return `<span class="tier ${esc(id)}" style="background:linear-gradient(90deg,${t.from},${t.to})"><span class="hx">${esc(t.en[0])}</span>${esc(t.en)}</span>`; };
const MED = ["🥇", "🥈", "🥉"];
let mode = "score";
$("week").innerHTML = W.map(w => `<option>${w}</option>`).join("") || "<option>-</option>";
$("legend").innerHTML = (D.tiers || []).map(t => `<span><b style="background:${t.from}"></b>${esc(t.en)} ${t.min}+</span>`).join("");
function leagues(){ const s = new Set((D.weeks[$("week").value] || []).map(e => e.league).filter(Boolean));
  $("league").innerHTML = `<option value="">All leagues</option>` + [...s].sort().map(l => `<option>${esc(l)}</option>`).join(""); }
function countUp(){ if (reduce) return; document.querySelectorAll("[data-n]").forEach(el => { const fin = parseFloat(el.dataset.n), t0 = performance.now(), sign = el.dataset.sign || "";
  const f = now => { const k = Math.min(1, (now - t0) / 900), v = fin * (1 - Math.pow(1 - k, 3)); el.textContent = sign + (Math.round(v * 10) / 10).toFixed(1);
    if (k < 1) requestAnimationFrame(f); else el.textContent = sign + fin.toFixed(1); }; requestAnimationFrame(f); }); }
function draw(){
  let rows = (D.weeks[$("week").value] || []).filter(e => !$("league").value || e.league === $("league").value);
  const all = rows.length;
  $("dist").innerHTML = (D.tiers || []).map(t => { const n = rows.filter(e => e.tier === t.id).length;
    return n ? `<i title="${esc(t.en)}: ${n}" style="width:${n / all * 100}%;background:linear-gradient(90deg,${t.from},${t.to})"></i>` : ""; }).join("");
  if (mode === "imp") rows = rows.filter(e => e.improvement != null).sort((a, b) => b.improvement - a.improvement);
  const val = e => mode === "imp" ? e.improvement : e.score, sign = e => mode === "imp" && e.improvement >= 0 ? "+" : "";
  if (!rows.length) { $("podium").innerHTML = ""; $("board").innerHTML = `<div class="empty">No submissions yet for this view.</div>`; return; }
  const top = rows.slice(0, 3), order = [1, 0, 2].filter(i => top[i]);
  $("podium").innerHTML = `<div class="podium">` + [1, 0, 2].map(i => { const e = top[i]; if (!e) return "<div></div>"; const t = T[e.tier] || {};
    return `<div class="pod p${i + 1}" style="background:linear-gradient(150deg,${t.from},${t.to})"><div class="m">${MED[i]}</div><div class="nm">${esc(e.nickname)}</div>
    <div class="sc" data-n="${val(e)}" data-sign="${sign(e)}">${sign(e)}${val(e)}</div><div class="tr">${esc(t.en || "")} · @${esc(e.login)}</div></div>`; }).join("") + `</div>`;
  $("board").innerHTML = `<table><tr><th>#</th><th>Name</th><th>Tier</th><th class="n">${mode === "imp" ? "Change" : "Score"}</th><th class="n hide">Quality</th><th class="n hide">Convos</th><th class="hide">League</th></tr>` +
    rows.map((e, i) => `<tr class="row" style="animation-delay:${Math.min(i, 20) * 40}ms"><td>${MED[i] || i + 1}</td><td>${esc(e.nickname)} <span class="chip">@${esc(e.login)}</span></td>
    <td>${badge(e.tier)}</td><td class="n"><b data-n="${val(e)}" data-sign="${sign(e)}">${sign(e)}${val(e)}</b></td><td class="n hide">${e.quality}</td>
    <td class="n hide">${e.conversations}</td><td class="hide chip">${esc(e.league)}</td></tr>`).join("") + `</table>`;
  countUp();
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
