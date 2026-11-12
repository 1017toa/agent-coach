"""Self-contained HTML report: no CDN, no JS framework, opens from disk."""
from __future__ import annotations

import html
import math
from datetime import datetime

E = lambda s: html.escape(str(s or ""))  # noqa: E731


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return iso[:10] if iso else ""


# ----------------------------------------------------------------- charts

def radar_svg(rubric: dict, cur: dict, prev: dict | None, size: int = 360) -> str:
    dims = rubric["dimensions"]
    n = len(dims)
    cx = cy = size / 2
    r = size / 2 - 64

    def pt(i, v):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * v / 100 * math.cos(a), cy + r * v / 100 * math.sin(a)

    parts = [f'<svg viewBox="0 0 {size} {size}" class="radar" role="img" aria-label="항목별 점수 레이더 차트">']
    for ring in (25, 50, 75, 100):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, ring) for i in range(n)))
        parts.append(f'<polygon points="{pts}" class="grid"/>')
    for i, d in enumerate(dims):
        x, y = pt(i, 100)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" class="grid"/>')
        lx, ly = pt(i, 122)
        anchor = "middle" if abs(lx - cx) < 8 else ("start" if lx > cx else "end")
        v = cur["dimensions"][d["id"]]["score"]
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" class="axis-label">'
                     f'{E(d["short"])}<tspan class="axis-val" x="{lx:.1f}" dy="1.2em">{"–" if v is None else v}</tspan></text>')

    def poly(run, cls):
        vals = [run["dimensions"][d["id"]]["score"] for d in dims]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, v or 0) for i, v in enumerate(vals)))
        out = [f'<polygon points="{pts}" class="{cls}"/>']
        if cls == "cur":
            for i, (d, v) in enumerate(zip(dims, vals)):
                if v is None:
                    continue
                x, y = pt(i, v)
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="cur-dot">'
                           f'<title>{E(d["name"])}: {v}점</title></circle>')
        return "".join(out)

    if prev:
        parts.append(poly(prev, "prev"))
    parts.append(poly(cur, "cur"))
    parts.append("</svg>")
    return "".join(parts)


def spark_svg(points: list[tuple[str, int | None]], w: int = 220, h: int = 64) -> str:
    pts = [(lbl, v) for lbl, v in points if v is not None]
    if not pts:
        return '<div class="muted small">기록 없음</div>'
    pad = 8
    n = len(pts)
    xs = [pad + (w - 2 * pad) * (i / (n - 1) if n > 1 else 0.5) for i in range(n)]
    ys = [h - pad - (h - 2 * pad) * v / 100 for _, v in pts]
    parts = [f'<svg viewBox="0 0 {w} {h}" class="spark" role="img" aria-label="회차별 점수 추이">',
             f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" class="grid"/>',
             f'<line x1="{pad}" y1="{h / 2}" x2="{w - pad}" y2="{h / 2}" class="grid dashed"/>']
    if n > 1:
        parts.append('<polyline class="trend" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys)) + '"/>')
    for (lbl, v), x, y in zip(pts, xs, ys):
        parts.append(f'<g class="hit"><circle cx="{x:.1f}" cy="{y:.1f}" r="12" class="hit-area"/>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="cur-dot"/>'
                     f'<title>{E(lbl)}: {v}점</title></g>')
    parts.append("</svg>")
    return "".join(parts)


# ----------------------------------------------------------------- page

CSS = """
:root{color-scheme:light;--bg:#f6f5f2;--surface:#fcfcfb;--line:#e4e2dc;--grid:#dcd9d2;
--text:#0b0b0b;--text2:#52514e;--muted:#7a7873;--accent:#2a78d6;--accent-soft:rgba(42,120,214,.14);
--prev:#9a978f;--good-bg:#e7f3ea;--good:#1f6b33;--bad-bg:#fbe9e7;--bad:#9b2c1f;--code:#f0eee9}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121211;--surface:#1a1a19;
--line:#2c2b29;--grid:#3a3936;--text:#f0efec;--text2:#c3c2b7;--muted:#8f8d86;--accent:#3987e5;--accent-soft:rgba(57,135,229,.2);
--prev:#77756e;--good-bg:#17301f;--good:#8fd6a3;--bad-bg:#3a1c18;--bad:#f1a397;--code:#232321}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--line:#2c2b29;--grid:#3a3936;--text:#f0efec;
--text2:#c3c2b7;--muted:#8f8d86;--accent:#3987e5;--accent-soft:rgba(57,135,229,.2);--prev:#77756e;--good-bg:#17301f;
--good:#8fd6a3;--bad-bg:#3a1c18;--bad:#f1a397;--code:#232321}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.6 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}h2{font-size:19px;margin:40px 0 12px}h3{font-size:16px;margin:0}
.muted{color:var(--muted)}.small{font-size:13px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px}
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:20px;margin-top:20px}
@media (max-width:760px){.hero{grid-template-columns:1fr}}
.score-big{font-size:64px;font-weight:700;line-height:1;letter-spacing:-.03em}
.delta{display:inline-block;font-size:14px;font-weight:600;padding:2px 8px;border-radius:99px;margin-left:8px;vertical-align:middle}
.delta.up{background:var(--good-bg);color:var(--good)}.delta.down{background:var(--bad-bg);color:var(--bad)}.delta.flat{background:var(--code);color:var(--text2)}
.legend{display:flex;gap:16px;font-size:13px;color:var(--text2);margin-top:8px}
.legend i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
svg .grid{fill:none;stroke:var(--grid);stroke-width:1}svg .dashed{stroke-dasharray:3 3}
svg .cur{fill:var(--accent-soft);stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
svg .prev{fill:none;stroke:var(--prev);stroke-width:2;stroke-dasharray:5 4}
svg .cur-dot{fill:var(--accent);stroke:var(--surface);stroke-width:2}
svg .trend{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
svg .hit-area{fill:transparent}svg .hit:hover .cur-dot{r:6}
.axis-label{font-size:12px;fill:var(--text2);font-weight:600}.axis-val{font-weight:400;fill:var(--muted)}
.radar{width:100%;max-width:380px;display:block;margin:0 auto}.spark{width:100%;height:64px;display:block}
.focus li{margin:6px 0}
.dims{display:grid;gap:16px}
.dim-head{display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap}
.dim-score{font-size:28px;font-weight:700}.bar{height:6px;background:var(--code);border-radius:99px;overflow:hidden;margin:10px 0}
.bar>span{display:block;height:100%;background:var(--accent);border-radius:99px}
.guide{font-size:13px;color:var(--text2);border-left:3px solid var(--line);padding-left:10px;margin:10px 0}
.guide a{color:var(--accent)}
.ex{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}@media (max-width:760px){.ex{grid-template-columns:1fr}}
.ex>div{border-radius:10px;padding:10px 12px;font-size:14px;white-space:pre-wrap;word-break:break-word}
.ex .before{background:var(--bad-bg)}.ex .after{background:var(--good-bg)}
.ex b{display:block;font-size:12px;margin-bottom:4px;color:var(--text2)}
.why{font-size:13px;color:var(--text2);margin-top:6px}
.meta{font-size:12px;color:var(--muted);margin-top:4px}
details{margin-top:10px}summary{cursor:pointer;color:var(--text2);font-size:14px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--text2);font-weight:600}td.num{text-align:center;font-variant-numeric:tabular-nums}
.tbl{overflow-x:auto}
.trends{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.trends .card{padding:14px}
footer{margin-top:48px;font-size:12px;color:var(--muted)}
"""


def _delta(cur, prev):
    if cur is None or prev is None:
        return ""
    d = cur - prev
    cls = "up" if d > 0 else "down" if d < 0 else "flat"
    sign = "+" if d > 0 else ""
    return f'<span class="delta {cls}">지난번 대비 {sign}{d}</span>'


def _normalize(runs: list[dict], rubric: dict) -> None:
    """Runs scored with an older rubric lack newer dimensions; show them as 'no data'."""
    for r in runs:
        dims = r.setdefault("dimensions", {})
        for d in rubric["dimensions"]:
            dims.setdefault(d["id"], {"score": None, "n": 0, "missed": 0})


def render(runs: list[dict], rubric: dict) -> str:
    _normalize(runs, rubric)
    cur = runs[-1]
    prev = runs[-2] if len(runs) > 1 else None
    dims = rubric["dimensions"]
    src_names = {"claude": "Claude Code", "codex": "Codex"}
    sources = ", ".join(src_names.get(s, s) for s in cur.get("sources", [])) or "-"

    scored = [(d, cur["dimensions"][d["id"]]) for d in dims if cur["dimensions"][d["id"]]["score"] is not None]
    weakest = sorted(scored, key=lambda x: x[1]["score"])[:3]
    strongest = sorted(scored, key=lambda x: -x[1]["score"])[:1]

    # coaching examples per dimension (judge rewrites first, then missed excerpts)
    coach: dict[str, list] = {d["id"]: [] for d in dims}
    missed: dict[str, list] = {d["id"]: [] for d in dims}
    for s in cur["sessions"]:
        for c in s.get("coaching", []):
            coach.setdefault(c["dimension"], []).append({**c, "session": s})
        for did, v in s["dimensions"].items():
            if v.get("score") == 0:
                missed.setdefault(did, []).append({**v, "session": s})

    h = [f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AI 코치 리포트</title>
<style>{CSS}</style></head><body><main>
<p class="muted small">agent-coach · {E(_fmt_date(cur['created']))} 채점 · {E(sources)} · 대화 {cur['session_count']}개 · 채점기 {E(cur['judge'])}</p>
<h1>나의 AI 지시 습관 리포트</h1>
<p class="muted">Anthropic·OpenAI 공식 가이드가 권하는 습관을 실제 내 대화에서 얼마나 지켰는지 봅니다.</p>
<section class="hero">
<div class="card"><div class="muted small">종합 점수</div>
<div><span class="score-big">{cur['overall'] if cur['overall'] is not None else '–'}</span>
<span class="muted">/ 100</span>{_delta(cur['overall'], prev and prev['overall'])}</div>
<h3 style="margin-top:20px">이번 주기에 집중할 것</h3><ol class="focus">"""]
    for d, v in weakest:
        h.append(f'<li><b>{E(d["name"])}</b> {v["score"]}점 — {E(d["summary"])}</li>')
    h.append("</ol>")
    if strongest:
        d, v = strongest[0]
        h.append(f'<p class="small muted">가장 잘하는 것: <b>{E(d["name"])}</b> ({v["score"]}점)</p>')
    h.append(f'</div><div class="card">{radar_svg(rubric, cur, prev)}<div class="legend">'
             f'<span><i style="background:var(--accent)"></i>이번 ({E(_fmt_date(cur["created"]))})</span>')
    if prev:
        h.append(f'<span><i style="background:var(--prev)"></i>지난번 ({E(_fmt_date(prev["created"]))})</span>')
    h.append("</div></div></section>")

    # trends
    h.append('<h2>회차별 변화</h2>')
    versions = sorted({r.get("rubric", {}).get("version", 1) for r in runs})
    if len(versions) > 1:
        h.append(f'<p class="muted small">회차마다 채점표 버전이 다릅니다(v{", v".join(map(str, versions))}). '
                 '새로 생긴 항목은 이전 회차에 점수가 없고, 종합 점수도 항목 수가 달라 그대로 비교하기 어렵습니다.</p>')
    if len(runs) < 2:
        h.append('<p class="muted small">아직 첫 회차입니다. 1~2주 뒤 <code>agent-coach run</code>을 다시 돌리면 그동안의 대화만 새로 채점해 변화를 그려 줍니다.</p>')
    h.append('<div class="trends">')
    series = [("종합", [(_fmt_date(r["created"]), r.get("overall")) for r in runs])]
    series += [(d["name"], [(_fmt_date(r["created"]), r["dimensions"].get(d["id"], {}).get("score")) for r in runs]) for d in dims]
    for name, pts in series:
        last = next((v for _, v in reversed(pts) if v is not None), None)
        h.append(f'<div class="card"><div class="dim-head"><h3>{E(name)}</h3><span class="muted small">{"–" if last is None else last}</span></div>{spark_svg(pts)}</div>')
    h.append("</div>")

    # dimension cards
    h.append('<h2>항목별 코칭</h2><div class="dims">')
    order = sorted(dims, key=lambda d: (cur["dimensions"][d["id"]]["score"] is None, cur["dimensions"][d["id"]]["score"] or 0))
    for d in order:
        v = cur["dimensions"][d["id"]]
        pv = prev["dimensions"].get(d["id"], {}).get("score") if prev else None
        sc = v["score"]
        h.append(f'<article class="card" id="{E(d["id"])}"><div class="dim-head"><div><h3>{E(d["name"])}</h3>'
                 f'<div class="small muted">{E(d["summary"])}</div></div>'
                 f'<div><span class="dim-score">{"–" if sc is None else sc}</span>{_delta(sc, pv)}</div></div>'
                 f'<div class="bar"><span style="width:{sc or 0}%"></span></div>'
                 f'<div class="small muted">해당 대화 {v["n"]}개 중 빠뜨림 {v["missed"]}개</div>')
        for g in d["guide"]:
            src = rubric["sources"][g["source"]]
            h.append(f'<div class="guide">{E(g["quote_ko"])}<br><a href="{E(src["url"])}" target="_blank" rel="noopener">{E(src["title"])} · {E(g["section"])}</a></div>')
        exs = coach.get(d["id"], [])[:3]
        if exs:
            h.append('<div class="small" style="margin-top:12px;font-weight:600">내 대화에서 고쳐 쓰기</div>')
            for c in exs:
                s = c["session"]
                h.append(f'<div class="ex"><div class="before"><b>실제로 쓴 지시 (turn {c["turn"]})</b>{E(c["original"])}</div>'
                         f'<div class="after"><b>이렇게 썼다면</b>{E(c["better"])}</div></div>'
                         f'<div class="why">{E(c["why"])}</div>'
                         f'<div class="meta">{E(src_names.get(s["source"], s["source"]))} · {E(s["project"])} · {E(_fmt_date(s["ended"]))} · {E(s["task_summary"])}</div>')
        else:
            ex = d.get("example") or {}
            if ex:
                h.append('<div class="small" style="margin-top:12px;font-weight:600">가이드 예시</div>'
                         f'<div class="ex"><div class="before"><b>대신에</b>{E(ex["before"])}</div>'
                         f'<div class="after"><b>이렇게</b>{E(ex["after"])}</div></div>')
        ms = missed.get(d["id"], [])
        if ms:
            h.append(f'<details><summary>빠뜨린 대화 {len(ms)}개 보기</summary><table><tr><th>날짜</th><th>대화</th><th>근거</th></tr>')
            for m in ms[:10]:
                s = m["session"]
                note = m.get("note") or ""
                exc = m.get("excerpt") or ""
                h.append(f'<tr><td>{E(_fmt_date(s["ended"]))}</td><td>{E(s["task_summary"])}<div class="meta">{E(s["project"])}</div></td>'
                         f'<td>{E(note)}{"<div class=meta>“" + E(exc) + "”</div>" if exc else ""}</td></tr>')
            h.append("</table></details>")
        h.append("</article>")
    h.append("</div>")

    # session table (also the table view of the chart data)
    h.append('<h2>채점한 대화</h2><div class="card tbl"><table><tr><th>날짜</th><th>도구</th><th>대화</th>')
    for d in dims:
        h.append(f'<th title="{E(d["name"])}">{E(d["short"])}</th>')
    h.append("</tr>")
    marks = {0: "✗", 1: "△", 2: "○", None: "·"}
    for s in cur["sessions"]:
        h.append(f'<tr><td>{E(_fmt_date(s["ended"]))}</td><td>{E(src_names.get(s["source"], s["source"]))}</td>'
                 f'<td>{E(s["task_summary"])}<div class="meta">{E(s["project"])} · {s["turns"]}턴</div></td>')
        for d in dims:
            v = s["dimensions"].get(d["id"], {})
            h.append(f'<td class="num" title="{E(v.get("note", ""))}">{marks.get(v.get("score"), "·")}</td>')
        h.append("</tr>")
    h.append('</table><p class="small muted">○ 잘함 · △ 부분 · ✗ 빠뜨림 · · 해당 없음. 칸에 마우스를 올리면 근거가 보입니다.</p></div>')

    h.append(f'<footer>모든 분석은 이 컴퓨터에서 이뤄졌고 결과는 <code>~/.agent-coach/</code>에만 저장됩니다. '
             f'채점표: {E(rubric["title"])} (v{rubric.get("version", 1)}).</footer></main></body></html>')
    return "".join(h)
