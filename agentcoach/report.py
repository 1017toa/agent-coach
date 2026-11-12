"""Self-contained HTML report: one screen, four tabs, no CDN, opens from disk.

Python only serialises the data; the page builds the views (overview, coaching,
conversations, trend) with a small vanilla-JS app so nothing has to scroll the
whole page. Each pane scrolls on its own, and on phones the list/detail panes
stack with a back button.
"""
from __future__ import annotations

import json


def _normalize(runs: list[dict], rubric: dict) -> None:
    """Runs scored with an older rubric lack newer dimensions; show them as 'no data'."""
    for r in runs:
        dims = r.setdefault("dimensions", {})
        for d in rubric["dimensions"]:
            dims.setdefault(d["id"], {"score": None, "n": 0, "missed": 0})


def _payload(runs: list[dict], rubric: dict) -> dict:
    slim_runs = [{k: r.get(k) for k in ("created", "overall", "dimensions", "judge", "session_count", "sources")}
                 | {"rubric_version": r.get("rubric", {}).get("version", 1)} for r in runs]
    cur = runs[-1]
    return {
        "rubric": {
            "title": rubric["title"], "version": rubric.get("version", 1),
            "sources": rubric["sources"],
            "dimensions": [{k: d.get(k) for k in ("id", "name", "short", "summary", "guide", "example")}
                           for d in rubric["dimensions"]],
        },
        "runs": slim_runs,
        "current": {k: cur.get(k) for k in ("created", "overall", "judge", "session_count", "sources", "sessions")},
    }


def render(runs: list[dict], rubric: dict) -> str:
    _normalize(runs, rubric)
    data = json.dumps(_payload(runs, rubric), ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("/*__DATA__*/null", data)


TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 코치 리포트</title>
<style>
:root{color-scheme:light;--bg:#f4f3ef;--surface:#fcfcfb;--surface2:#f0eee9;--line:#e2e0d9;--grid:#dcd9d2;
--text:#0b0b0b;--text2:#52514e;--muted:#7a7873;--accent:#2a78d6;--accent-soft:rgba(42,120,214,.13);
--prev:#9a978f;--good-bg:#e5f2e8;--good:#1f6b33;--bad-bg:#fae8e5;--bad:#9b2c1f;--warn:#8a5a00;--warn-bg:#fbf0d9}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#111110;--surface:#1a1a19;
--surface2:#232321;--line:#2e2d2a;--grid:#3a3936;--text:#f0efec;--text2:#c3c2b7;--muted:#8f8d86;--accent:#3987e5;
--accent-soft:rgba(57,135,229,.2);--prev:#77756e;--good-bg:#16301e;--good:#8fd6a3;--bad-bg:#3a1c18;--bad:#f1a397;--warn:#f0c46a;--warn-bg:#352a12}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#111110;--surface:#1a1a19;--surface2:#232321;--line:#2e2d2a;--grid:#3a3936;
--text:#f0efec;--text2:#c3c2b7;--muted:#8f8d86;--accent:#3987e5;--accent-soft:rgba(57,135,229,.2);--prev:#77756e;
--good-bg:#16301e;--good:#8fd6a3;--bad-bg:#3a1c18;--bad:#f1a397;--warn:#f0c46a;--warn-bg:#352a12}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.55 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
display:flex;flex-direction:column;overflow:hidden}
button{font:inherit;color:inherit}
a{color:var(--accent)}
.muted{color:var(--muted)}.small{font-size:12px}
/* top bar */
header{display:flex;align-items:center;gap:16px;padding:10px 20px;border-bottom:1px solid var(--line);background:var(--surface);flex-wrap:wrap}
.brand{font-weight:700;font-size:15px;white-space:nowrap}
.kpi{display:flex;align-items:baseline;gap:6px}
.kpi b{font-size:22px;letter-spacing:-.02em}
.meta{color:var(--muted);font-size:12px;flex:1;min-width:160px}
.iconbtn{border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:5px 10px;cursor:pointer}
nav.tabs{display:flex;gap:2px;padding:0 16px;background:var(--surface);border-bottom:1px solid var(--line);overflow-x:auto}
nav.tabs button{border:0;background:none;padding:10px 14px;cursor:pointer;color:var(--text2);border-bottom:2px solid transparent;white-space:nowrap}
nav.tabs button[aria-selected="true"]{color:var(--text);border-bottom-color:var(--accent);font-weight:600}
main{flex:1;min-height:0;padding:16px 20px}
.view{height:100%;display:none}
.view.on{display:grid}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;min-height:0}
.scroll{overflow:auto}
h2{font-size:15px;margin:0 0 10px}h3{font-size:14px;margin:0}
/* overview */
#v-overview{grid-template-columns:minmax(240px,1fr) minmax(300px,1.3fr) minmax(260px,1.1fr);gap:16px}
.big{font-size:56px;font-weight:700;line-height:1;letter-spacing:-.03em}
.delta{display:inline-block;font-size:12px;font-weight:600;padding:2px 8px;border-radius:99px;margin-left:6px;vertical-align:middle}
.delta.up{background:var(--good-bg);color:var(--good)}.delta.down{background:var(--bad-bg);color:var(--bad)}.delta.flat{background:var(--surface2);color:var(--text2)}
.focus{margin:8px 0 0;padding-left:18px}.focus li{margin:8px 0}
.focus button{all:unset;cursor:pointer;font-weight:600;color:var(--text)}.focus button:hover{color:var(--accent)}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:14px 0}
.tiles button{all:unset;cursor:pointer;background:var(--surface2);border-radius:10px;padding:10px;text-align:left}
.tiles button:hover{outline:1px solid var(--line)}
.tiles b{display:block;font-size:22px;line-height:1.2}.tiles span{font-size:12px;color:var(--text2)}
.radar{width:100%;height:100%;max-height:440px;display:block}
.grid{fill:none;stroke:var(--grid);stroke-width:1}
.cur{fill:var(--accent-soft);stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
.prev{fill:none;stroke:var(--prev);stroke-width:2;stroke-dasharray:5 4}
.dot{fill:var(--accent);stroke:var(--surface);stroke-width:2;cursor:pointer}
.axis{font-size:11px;fill:var(--text2);font-weight:600;cursor:pointer}.axis tspan{font-weight:400;fill:var(--muted)}
.legend{display:flex;gap:14px;font-size:12px;color:var(--text2);justify-content:center}
.legend i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
.barlist{list-style:none;margin:0;padding:0}
.barlist li{display:grid;grid-template-columns:1fr 34px;gap:2px 10px;align-items:center;padding:7px 8px;border-radius:8px;cursor:pointer}
.barlist li:hover,.barlist li[aria-current="true"]{background:var(--surface2)}
.barlist .nm{font-size:13px}.barlist .sc{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}
.bar{grid-column:1/-1;height:5px;background:var(--surface2);border-radius:99px;overflow:hidden}
.bar span{display:block;height:100%;background:var(--accent);border-radius:99px}
.barlist li[aria-current="true"] .bar{background:var(--bg)}
.na{color:var(--muted);font-weight:400}
/* master-detail */
.md{grid-template-columns:minmax(240px,320px) 1fr;gap:16px}
.md>.card{display:flex;flex-direction:column}
.list{flex:1;min-height:0}
.detail{overflow:auto}
.back{display:none}
.chip{display:inline-block;font-size:11px;padding:1px 8px;border-radius:99px;background:var(--surface2);color:var(--text2);margin-right:4px}
.guide{font-size:13px;color:var(--text2);border-left:3px solid var(--line);padding:2px 0 2px 10px;margin:8px 0}
.ex{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.ex>div{border-radius:10px;padding:10px 12px;white-space:pre-wrap;word-break:break-word}
.ex .before{background:var(--bad-bg)}.ex .after{background:var(--good-bg)}
.ex b{display:block;font-size:11px;margin-bottom:4px;color:var(--text2)}
.why{font-size:13px;color:var(--text2);margin-top:6px}
.sess{font-size:12px;color:var(--muted);margin-top:4px}
.coach{padding:12px 0;border-top:1px solid var(--line)}.coach:first-of-type{border-top:0}
details{margin-top:12px}summary{cursor:pointer;color:var(--text2)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--text2);font-weight:600}
.slist{list-style:none;margin:0;padding:0}
.slist li{padding:9px 8px;border-radius:8px;cursor:pointer;border-bottom:1px solid var(--line)}
.slist li:hover,.slist li[aria-current="true"]{background:var(--surface2)}
.marks{font-family:ui-monospace,Consolas,monospace;font-size:12px;letter-spacing:2px;color:var(--text2)}
.toolbar{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.toolbar input,.toolbar select{flex:1;min-width:120px;border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:6px 10px;font:inherit;color:inherit}
.score-row{display:grid;grid-template-columns:110px 44px 1fr;gap:8px;padding:8px 0;border-bottom:1px solid var(--line);align-items:start}
.pill{font-size:12px;font-weight:600;text-align:center;border-radius:6px;padding:1px 0}
.p2{background:var(--good-bg);color:var(--good)}.p1{background:var(--warn-bg);color:var(--warn)}.p0{background:var(--bad-bg);color:var(--bad)}.pn{background:var(--surface2);color:var(--muted)}
/* trend */
#v-trend{grid-template-rows:auto 1fr;gap:16px}
.trends{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;align-content:start}
.trends .card{padding:12px}
.spark{width:100%;height:56px;display:block}
.trend{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.note{font-size:12px;color:var(--muted);margin:0}
/* responsive */
@media (max-width:1100px){#v-overview{grid-template-columns:1fr 1fr}#v-overview .c-dims{grid-column:1/-1}}
@media (max-width:760px){
 body{overflow:auto;height:auto}
 header{padding:10px 16px;gap:10px}
 main{padding:12px 16px}
 .view.on{display:block}
 .view>.card,.view>.trends{margin-bottom:12px}
 #v-overview .c-radar{min-height:340px}
 .md>.card{max-height:none}
 .md.showing .c-list{display:none}
 .md:not(.showing) .c-detail{display:none}
 .back{display:inline-block;margin-bottom:10px}
 .ex{grid-template-columns:1fr}
 .score-row{grid-template-columns:96px 40px 1fr}
}
</style></head>
<body>
<header>
 <div class="brand">agent-coach</div>
 <div class="kpi"><span class="muted small">종합</span><b id="kpi-score">–</b><span class="muted small">/100</span><span id="kpi-delta"></span></div>
 <div class="meta" id="meta"></div>
 <button class="iconbtn" id="theme" title="밝게/어둡게">◐</button>
</header>
<nav class="tabs" role="tablist">
 <button role="tab" data-tab="overview">개요</button>
 <button role="tab" data-tab="coach">항목별 코칭</button>
 <button role="tab" data-tab="sessions">대화별 결과</button>
 <button role="tab" data-tab="trend">회차별 변화</button>
</nav>
<main>
 <section class="view" id="v-overview">
  <div class="card scroll">
   <h2>이번 주기에 집중할 것</h2>
   <ol class="focus" id="focus"></ol>
   <p class="small muted" id="best"></p>
   <div class="tiles" id="tiles"></div>
   <p class="small muted" id="about"></p>
  </div>
  <div class="card c-radar" style="display:flex;flex-direction:column">
   <h2>항목별 점수</h2>
   <div style="flex:1;min-height:0" id="radar"></div>
   <div class="legend" id="legend"></div>
  </div>
  <div class="card scroll c-dims">
   <h2>약한 순서 <span class="muted small">눌러서 코칭 보기</span></h2>
   <ul class="barlist" id="ov-dims"></ul>
  </div>
 </section>

 <section class="view md" id="v-coach">
  <div class="card c-list"><h2>항목</h2><ul class="barlist list scroll" id="coach-list"></ul></div>
  <div class="card c-detail detail" id="coach-detail"></div>
 </section>

 <section class="view md" id="v-sessions">
  <div class="card c-list">
   <div class="toolbar"><input id="q" type="search" placeholder="대화 검색"><select id="filter"></select></div>
   <ul class="slist list scroll" id="sess-list"></ul>
  </div>
  <div class="card c-detail detail" id="sess-detail"></div>
 </section>

 <section class="view" id="v-trend">
  <p class="note" id="trend-note"></p>
  <div class="trends scroll" id="trends"></div>
 </section>
</main>
<script id="data" type="application/json">/*__DATA__*/null</script>
<script>
(() => {
const D = JSON.parse(document.getElementById("data").textContent);
const dims = D.rubric.dimensions, runs = D.runs, cur = runs[runs.length - 1], prev = runs.length > 1 ? runs[runs.length - 2] : null;
const sessions = D.current.sessions || [];
const SRC = {claude: "Claude Code", codex: "Codex"};
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const day = s => (s || "").slice(0, 10);
const sc = id => cur.dimensions[id] ? cur.dimensions[id].score : null;
const delta = (a, b) => (a == null || b == null) ? "" :
  `<span class="delta ${a > b ? "up" : a < b ? "down" : "flat"}">${a > b ? "+" : ""}${a - b}</span>`;
const pill = v => `<span class="pill ${v == null ? "pn" : "p" + v}">${v == null ? "–" : ["빠뜨림", "부분", "잘함"][v]}</span>`;
const store = {get(k){try{return localStorage.getItem(k)}catch(e){return null}}, set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};

/* ---------- header ---------- */
$("#kpi-score").textContent = cur.overall ?? "–";
$("#kpi-delta").innerHTML = prev && prev.rubric_version === cur.rubric_version ? delta(cur.overall, prev.overall) : "";
$("#meta").textContent = `${day(D.current.created)} 채점 · ${(D.current.sources || []).map(s => SRC[s] || s).join(", ")} · 대화 ${D.current.session_count}개 · ${D.current.judge} · 채점표 v${D.rubric.version}`;
const theme = store.get("ac-theme"); if (theme) document.documentElement.dataset.theme = theme;
$("#theme").onclick = () => {
  const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "light" : "dark"; store.set("ac-theme", document.documentElement.dataset.theme);
};

/* ---------- routing ---------- */
const views = ["overview", "coach", "sessions", "trend"];
function go(tab, arg, push = true) {
  if (!views.includes(tab)) tab = "overview";
  document.querySelectorAll("nav.tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("on", v.id === "v-" + tab));
  if (tab === "coach") showDim(arg || state.dim, !!arg);
  if (tab === "sessions") showSession(arg || state.sess, !!arg);
  if (push) history.replaceState(null, "", "#" + tab + (arg ? "/" + arg : ""));
}
document.querySelectorAll("nav.tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll(".md").forEach(m => m.classList.remove("showing")); go(b.dataset.tab);
});
const state = {dim: null, sess: null};

/* ---------- overview ---------- */
const ranked = dims.filter(d => sc(d.id) != null).sort((a, b) => sc(a.id) - sc(b.id));
const unscored = dims.filter(d => sc(d.id) == null);
$("#focus").innerHTML = ranked.slice(0, 3).map(d =>
  `<li><button data-dim="${d.id}">${esc(d.name)}</button> <span class="muted">${sc(d.id)}점</span><div class="small muted">${esc(d.summary)}</div></li>`).join("");
const best = ranked[ranked.length - 1];
$("#best").innerHTML = best ? `가장 잘하는 것: <b>${esc(best.name)}</b> (${sc(best.id)}점)` : "";
const nCoach = sessions.reduce((a, s) => a + (s.coaching || []).length, 0);
const nMissed = sessions.reduce((a, s) => a + Object.values(s.dimensions || {}).filter(v => v.score === 0).length, 0);
$("#tiles").innerHTML = `<button data-go="sessions"><b>${sessions.length}</b><span>채점한 대화</span></button>
 <button data-go="coach"><b>${nCoach}</b><span>고쳐 쓰기 예시</span></button>
 <button data-go="sessions"><b>${nMissed}</b><span>빠뜨린 판정</span></button>`;
document.querySelectorAll("[data-go]").forEach(b => b.onclick = () => go(b.dataset.go));
$("#about").innerHTML =`${esc(D.rubric.title)}. 점수는 해당 항목이 필요했던 대화만 평균 낸 값입니다.`;
const barItem = d => {
  const v = sc(d.id), n = cur.dimensions[d.id] || {};
  return `<li data-dim="${d.id}"><span class="nm">${esc(d.name)} <span class="small muted">${n.n ? n.n + "개 대화" : ""}</span></span>
  <span class="sc">${v == null ? '<span class="na">–</span>' : v}</span><span class="bar"><span style="width:${v || 0}%"></span></span></li>`;
};
$("#ov-dims").innerHTML = ranked.concat(unscored).map(barItem).join("");
document.addEventListener("click", e => {
  const el = e.target.closest("[data-dim]");
  if (el && !el.closest("#coach-list")) go("coach", el.dataset.dim);
});

function radar() {
  const n = dims.length, W = 420, H = 400, cx = W / 2, cy = H / 2 + 4, r = 140;
  const pt = (i, v) => { const a = -Math.PI / 2 + 2 * Math.PI * i / n; return [cx + r * v / 100 * Math.cos(a), cy + r * v / 100 * Math.sin(a)]; };
  let s = `<svg viewBox="0 0 ${W} ${H}" class="radar" role="img" aria-label="항목별 점수 레이더 차트">`;
  for (const ring of [25, 50, 75, 100]) s += `<polygon class="grid" points="${dims.map((_, i) => pt(i, ring).join(",")).join(" ")}"/>`;
  dims.forEach((d, i) => {
    const [x, y] = pt(i, 100), [lx, ly] = pt(i, 121), v = sc(d.id);
    const anchor = Math.abs(lx - cx) < 8 ? "middle" : lx > cx ? "start" : "end";
    s += `<line class="grid" x1="${cx}" y1="${cy}" x2="${x}" y2="${y}"/>`;
    s += `<text class="axis" data-dim="${d.id}" x="${lx}" y="${ly}" text-anchor="${anchor}">${esc(d.short)}<tspan x="${lx}" dy="1.2em">${v ?? "–"}</tspan></text>`;
  });
  const poly = (run, cls) => `<polygon class="${cls}" points="${dims.map((d, i) => pt(i, (run.dimensions[d.id] || {}).score || 0).join(",")).join(" ")}"/>`;
  if (prev) s += poly(prev, "prev");
  s += poly(cur, "cur");
  dims.forEach((d, i) => { const v = sc(d.id); if (v == null) return; const [x, y] = pt(i, v);
    s += `<circle class="dot" data-dim="${d.id}" cx="${x}" cy="${y}" r="5"><title>${esc(d.name)}: ${v}점</title></circle>`; });
  $("#radar").innerHTML = s + "</svg>";
  $("#legend").innerHTML = `<span><i style="background:var(--accent)"></i>이번 ${day(cur.created)}</span>` +
    (prev ? `<span><i style="background:var(--prev)"></i>지난번 ${day(prev.created)}</span>` : "");
}
radar();

/* ---------- coaching ---------- */
const coachBy = {}, missedBy = {};
for (const s of sessions) {
  for (const c of s.coaching || []) (coachBy[c.dimension] ||= []).push({...c, s});
  for (const [id, v] of Object.entries(s.dimensions || {})) if (v.score === 0) (missedBy[id] ||= []).push({...v, s});
}
$("#coach-list").innerHTML = ranked.concat(unscored).map(barItem).join("");
$("#coach-list").addEventListener("click", e => { const li = e.target.closest("li[data-dim]"); if (li) go("coach", li.dataset.dim); });
const sessLine = s => `${esc(SRC[s.source] || s.source)} · ${esc(s.project)} · ${day(s.ended)} · ${esc(s.task_summary)}`;
function showDim(id, open) {
  id = id || (ranked[0] || dims[0]).id; state.dim = id;
  const d = dims.find(x => x.id === id); if (!d) return;
  document.querySelectorAll("#coach-list li").forEach(li => li.setAttribute("aria-current", li.dataset.dim === id));
  const v = cur.dimensions[id] || {}, pv = prev && prev.rubric_version === cur.rubric_version ? (prev.dimensions[id] || {}).score : null;
  const ex = coachBy[id] || [], ms = missedBy[id] || [];
  let h = `<button class="iconbtn back" data-back>← 항목 목록</button>
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap">
   <div><h2 style="font-size:18px;margin:0">${esc(d.name)}</h2><div class="muted">${esc(d.summary)}</div></div>
   <div><span class="big" style="font-size:40px">${v.score ?? "–"}</span>${delta(v.score, pv)}</div></div>
  <div class="small muted" style="margin:6px 0 4px">해당 대화 ${v.n || 0}개 · 빠뜨림 ${v.missed || 0}개</div>`;
  if (ex.length) {
    h += `<h3 style="margin-top:14px">내 대화에서 고쳐 쓰기 <span class="chip">${ex.length}</span></h3>`;
    h += ex.map(c => `<div class="coach"><div class="ex"><div class="before"><b>실제로 쓴 지시 · turn ${c.turn}</b>${esc(c.original)}</div>
      <div class="after"><b>이렇게 썼다면</b>${esc(c.better)}</div></div><div class="why">${esc(c.why)}</div>
      <div class="sess"><a href="#sessions/${esc(c.s.id)}" data-sess="${esc(c.s.id)}">${sessLine(c.s)}</a></div></div>`).join("");
  } else if (d.example) {
    h += `<h3 style="margin-top:14px">가이드 예시</h3><div class="ex"><div class="before"><b>대신에</b>${esc(d.example.before)}</div><div class="after"><b>이렇게</b>${esc(d.example.after)}</div></div>`;
  }
  h += `<details ${ex.length ? "" : "open"}><summary>공식 가이드 근거 ${d.guide.length}개</summary>` + d.guide.map(g => {
    const src = D.rubric.sources[g.source] || {}; return `<div class="guide">${esc(g.quote_ko)}<br><a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(src.title)} · ${esc(g.section)}</a></div>`;
  }).join("") + `</details>`;
  if (ms.length) h += `<details><summary>빠뜨린 대화 ${ms.length}개</summary><table><tr><th>대화</th><th>근거</th></tr>` +
    ms.map(m => `<tr><td><a href="#sessions/${esc(m.s.id)}" data-sess="${esc(m.s.id)}">${esc(m.s.task_summary)}</a><div class="sess">${day(m.s.ended)} · ${esc(m.s.project)}</div></td><td>${esc(m.note)}${m.excerpt ? `<div class="sess">“${esc(m.excerpt)}”</div>` : ""}</td></tr>`).join("") + `</table></details>`;
  $("#coach-detail").innerHTML = h; $("#coach-detail").scrollTop = 0;
  if (open) $("#v-coach").classList.add("showing");
}

/* ---------- sessions ---------- */
$("#filter").innerHTML = `<option value="">모든 항목</option>` + dims.map(d => `<option value="${d.id}">${esc(d.short)} 빠뜨린 대화</option>`).join("");
const markOf = v => v == null ? "·" : ["✗", "△", "○"][v];
function listSessions() {
  const q = $("#q").value.trim().toLowerCase(), f = $("#filter").value;
  const rows = sessions.filter(s => (!q || (s.task_summary + " " + s.project).toLowerCase().includes(q)) &&
    (!f || (s.dimensions[f] || {}).score === 0));
  $("#sess-list").innerHTML = rows.map(s => `<li data-id="${esc(s.id)}"><div>${esc(s.task_summary)}</div>
    <div class="sess">${day(s.ended)} · ${esc(SRC[s.source] || s.source)} · ${s.turns}턴</div>
    <div class="marks" title="${dims.map(d => d.short).join(" ")}">${dims.map(d => markOf((s.dimensions[d.id] || {}).score)).join("")}</div></li>`).join("")
    || `<li class="muted">조건에 맞는 대화가 없습니다</li>`;
  document.querySelectorAll("#sess-list li[data-id]").forEach(li => li.setAttribute("aria-current", li.dataset.id === state.sess));
}
$("#q").oninput = listSessions; $("#filter").onchange = listSessions;
$("#sess-list").addEventListener("click", e => { const li = e.target.closest("li[data-id]"); if (li) go("sessions", li.dataset.id); });
document.addEventListener("click", e => { const a = e.target.closest("[data-sess]"); if (a) { e.preventDefault(); go("sessions", a.dataset.sess); } });
function showSession(id, open) {
  listSessions();
  const s = sessions.find(x => x.id === id) || sessions[0]; if (!s) { $("#sess-detail").innerHTML = '<p class="muted">채점한 대화가 없습니다.</p>'; return; }
  state.sess = s.id;
  document.querySelectorAll("#sess-list li[data-id]").forEach(li => li.setAttribute("aria-current", li.dataset.id === s.id));
  let h = `<button class="iconbtn back" data-back>← 대화 목록</button>
   <h2 style="font-size:17px;margin:0">${esc(s.task_summary)}</h2>
   <div class="sess" style="margin-bottom:10px">${esc(SRC[s.source] || s.source)} · ${esc(s.project)} · ${day(s.started)} ~ ${day(s.ended)} · ${s.turns}턴</div>`;
  if ((s.coaching || []).length) h += `<h3>이 대화의 고쳐 쓰기</h3>` + s.coaching.map(c => {
    const d = dims.find(x => x.id === c.dimension) || {}; return `<div class="coach"><span class="chip">${esc(d.name || c.dimension)}</span>
    <div class="ex"><div class="before"><b>실제로 쓴 지시 · turn ${c.turn}</b>${esc(c.original)}</div><div class="after"><b>이렇게 썼다면</b>${esc(c.better)}</div></div><div class="why">${esc(c.why)}</div></div>`; }).join("");
  h += `<h3 style="margin-top:14px">항목별 판정</h3>` + dims.map(d => { const v = s.dimensions[d.id] || {};
    return `<div class="score-row"><a href="#coach/${d.id}" data-dim="${d.id}">${esc(d.name)}</a>${pill(v.score)}<div>${esc(v.note || (v.score == null ? "해당 없음" : ""))}${v.excerpt ? `<div class="sess">turn ${v.evidence_turn}: “${esc(v.excerpt)}”</div>` : ""}</div></div>`; }).join("");
  $("#sess-detail").innerHTML = h; $("#sess-detail").scrollTop = 0;
  if (open) $("#v-sessions").classList.add("showing");
}
document.addEventListener("click", e => { if (e.target.closest("[data-back]")) document.querySelectorAll(".md").forEach(m => m.classList.remove("showing")); });

/* ---------- trend ---------- */
const versions = [...new Set(runs.map(r => r.rubric_version))];
$("#trend-note").textContent = runs.length < 2
  ? "아직 첫 회차입니다. 1~2주 뒤 agent-coach run 을 다시 돌리면 그 사이 대화만 채점해 변화가 쌓입니다."
  : versions.length > 1 ? `회차마다 채점표 버전이 다릅니다(v${versions.join(", v")}). 새 항목은 이전 회차에 점수가 없습니다.` : `${runs.length}회차 기록`;
function spark(pts) {
  const p = pts.filter(x => x[1] != null); if (!p.length) return '<div class="muted small">기록 없음</div>';
  const W = 200, H = 56, pad = 8, xs = p.map((_, i) => pad + (W - 2 * pad) * (p.length > 1 ? i / (p.length - 1) : .5)), ys = p.map(x => H - pad - (H - 2 * pad) * x[1] / 100);
  let s = `<svg viewBox="0 0 ${W} ${H}" class="spark" role="img" aria-label="회차별 점수"><line class="grid" x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}"/>`;
  if (p.length > 1) s += `<polyline class="trend" points="${xs.map((x, i) => x + "," + ys[i]).join(" ")}"/>`;
  p.forEach((x, i) => s += `<circle class="dot" cx="${xs[i]}" cy="${ys[i]}" r="4"><title>${x[0]}: ${x[1]}점</title></circle>`);
  return s + "</svg>";
}
const series = [["종합", null, runs.map(r => [day(r.created), r.overall])]].concat(dims.map(d => [d.name, d.id, runs.map(r => [day(r.created), (r.dimensions[d.id] || {}).score])]));
$("#trends").innerHTML = series.map(([name, id, pts]) => { const last = [...pts].reverse().find(x => x[1] != null);
  return `<div class="card"${id ? ` data-dim="${id}" style="cursor:pointer"` : ""}><div style="display:flex;justify-content:space-between"><h3>${esc(name)}</h3><span class="muted">${last ? last[1] : "–"}</span></div>${spark(pts)}</div>`; }).join("");

/* ---------- start ---------- */
const [tab, arg] = (location.hash.slice(1) || "overview").split("/");
go(tab, arg, false);
if (matchMedia("(max-width:760px)").matches && !arg) document.querySelectorAll(".md").forEach(m => m.classList.remove("showing"));
})();
</script>
</body></html>
"""
