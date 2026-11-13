"""Self-contained HTML report: one screen, four tabs, no CDN, opens from disk.

Python only serialises the data; the page builds the views (overview, coaching,
conversations, trend) with a small vanilla-JS app so nothing has to scroll the
whole page. Each pane scrolls on its own, and on phones the list/detail panes
stack with a back button.
"""
from __future__ import annotations

import json
import re


def _normalize(runs: list[dict], rubric: dict) -> None:
    """Runs scored with an older rubric lack newer dimensions; show them as 'no data'."""
    for r in runs:
        dims = r.setdefault("dimensions", {})
        for d in rubric["dimensions"]:
            dims.setdefault(d["id"], {"score": None, "n": 0, "missed": 0})


def _payload(runs: list[dict], rubric: dict) -> dict:
    slim_runs = [{k: r.get(k) for k in ("created", "overall", "dimensions", "judge", "session_count", "sources")}
                 | {"gap_share": (r.get("misses") or {}).get("gap_share"),
                    "gaps_per_100_turns": (r.get("misses") or {}).get("gaps_per_100_turns")}
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
        "current": {k: cur.get(k) for k in ("created", "overall", "judge", "session_count", "sources", "sessions", "misses")},
    }


def render(runs: list[dict], rubric: dict) -> str:
    _normalize(runs, rubric)
    lang = rubric.get("lang", "ko")
    data = json.dumps(_payload(runs, rubric), ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("{{html_lang}}", lang)
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: UI[m.group(1)].get(lang) or UI[m.group(1)]["en"], html)
    return html.replace("/*__DATA__*/null", data)


UI = {
    'you_wrote_m': {'ko': '<b>실제로 쓴 지시 · turn ${m.turn}</b>', 'en': '<b>What you wrote · turn ${m.turn}</b>'},
    'title': {'ko': '<title>AI 코치 리포트</title>', 'en': '<title>agent-coach report</title>'},
    'overall': {'ko': '<span class="muted small">종합</span>', 'en': '<span class="muted small">Overall</span>'},
    'theme_btn': {'ko': 'title="밝게/어둡게"', 'en': 'title="Light / dark"'},
    'tab_overview': {'ko': 'data-tab="overview">개요<', 'en': 'data-tab="overview">Overview<'},
    'tab_coach': {'ko': 'data-tab="coach">항목별 코칭<', 'en': 'data-tab="coach">Coaching<'},
    'tab_misses': {'ko': 'data-tab="misses">놓친 응답<', 'en': 'data-tab="misses">Missed responses<'},
    'tab_sessions': {'ko': 'data-tab="sessions">대화별 결과<', 'en': 'data-tab="sessions">Conversations<'},
    'tab_trend': {'ko': 'data-tab="trend">회차별 변화<', 'en': 'data-tab="trend">Progress<'},
    'focus_h': {'ko': '<h2>이번 주기에 집중할 것</h2>', 'en': '<h2>Focus on this cycle</h2>'},
    'radar_h': {'ko': '<h2>항목별 점수</h2>', 'en': '<h2>Scores by habit</h2>'},
    'weak_h': {'ko': '<h2>약한 순서 <span class="muted small">눌러서 코칭 보기</span></h2>', 'en': '<h2>Weakest first <span class="muted small">click for coaching</span></h2>'},
    'dims_h': {'ko': '<h2>항목</h2>', 'en': '<h2>Habits</h2>'},
    'search_ph': {'ko': 'placeholder="대화 검색"', 'en': 'placeholder="Search conversations"'},
    'pill': {'ko': '["빠뜨림", "부분", "잘함"]', 'en': '["Missed", "Partial", "Good"]'},
    'meta': {'ko': '`${day(D.current.created)} 채점 · ${(D.current.sources || []).map(s => SRC[s] || s).join(", ")} · 대화 ${D.current.session_count}개 · ${D.current.judge} · 채점표 v${D.rubric.version}`', 'en': '`Graded ${day(D.current.created)} · ${(D.current.sources || []).map(s => SRC[s] || s).join(", ")} · ${D.current.session_count} conversations · ${D.current.judge} · rubric v${D.rubric.version}`'},
    'pts1': {'ko': '<span class="muted">${sc(d.id)}점</span>', 'en': '<span class="muted">${sc(d.id)}</span>'},
    'best': {'ko': '`가장 잘하는 것: <b>${esc(best.name)}</b> (${sc(best.id)}점)`', 'en': '`Strongest: <b>${esc(best.name)}</b> (${sc(best.id)})`'},
    'tile1': {'ko': '<span>채점한 대화</span>', 'en': '<span>conversations graded</span>'},
    'tile2': {'ko': '<span>고쳐 쓰기 예시</span>', 'en': '<span>rewrites of your prompts</span>'},
    'tile3': {'ko': '<span>놓친 응답 중 내 지시 빈틈</span>', 'en': '<span>missed responses that were prompt gaps</span>'},
    'about': {'ko': '점수는 해당 항목이 필요했던 대화만 평균 낸 값입니다.', 'en': 'Each score averages only the conversations where that habit mattered.'},
    'nconv': {'ko': '${n.n ? n.n + "개 대화" : ""}', 'en': '${n.n ? n.n + " convos" : ""}'},
    'radar_aria': {'ko': 'aria-label="항목별 점수 레이더 차트"', 'en': 'aria-label="Radar chart of scores by habit"'},
    'pts2': {'ko': '${esc(d.name)}: ${v}점</title>', 'en': '${esc(d.name)}: ${v}</title>'},
    'legend_cur': {'ko': '></i>이번 ${day(cur.created)}', 'en': '></i>This run ${day(cur.created)}'},
    'legend_prev': {'ko': '></i>지난번 ${day(prev.created)}', 'en': '></i>Previous ${day(prev.created)}'},
    'back_dims': {'ko': '← 항목 목록', 'en': '← Habits'},
    'dim_counts': {'ko': '해당 대화 ${v.n || 0}개 · 빠뜨림 ${v.missed || 0}개', 'en': '${v.n || 0} relevant conversations · missed in ${v.missed || 0}'},
    'rewrites_h': {'ko': '내 대화에서 고쳐 쓰기 <span', 'en': 'Rewrites from your conversations <span'},
    'you_wrote': {'ko': '<b>실제로 쓴 지시 · turn ${c.turn}</b>', 'en': '<b>What you wrote · turn ${c.turn}</b>'},
    'better': {'ko': '<b>이렇게 썼다면</b>', 'en': '<b>Better</b>'},
    'guide_ex_h': {'ko': '가이드 예시</h3>', 'en': 'Example from the guide</h3>'},
    'instead': {'ko': '<b>대신에</b>', 'en': '<b>Instead of</b>'},
    'try': {'ko': '<b>이렇게</b>', 'en': '<b>Try</b>'},
    'guide_n': {'ko': '공식 가이드 근거 ${d.guide.length}개', 'en': 'Official guidance (${d.guide.length})'},
    'missed_n': {'ko': '빠뜨린 대화 ${ms.length}개</summary><table><tr><th>대화</th><th>근거</th></tr>', 'en': 'Conversations that missed it (${ms.length})</summary><table><tr><th>Conversation</th><th>Why</th></tr>'},
    'all_dims': {'ko': '<option value="">모든 항목</option>', 'en': '<option value="">All habits</option>'},
    'missed_opt': {'ko': '${esc(d.short)} 빠뜨린 대화</option>', 'en': 'Missed: ${esc(d.short)}</option>'},
    'turns1': {'ko': '· ${s.turns}턴</div>\n    <div class="marks"', 'en': '· ${s.turns} turns</div>\n    <div class="marks"'},
    'no_match': {'ko': '조건에 맞는 대화가 없습니다', 'en': 'No matching conversations'},
    'no_sess': {'ko': '채점한 대화가 없습니다.', 'en': 'No conversations graded.'},
    'back_sess': {'ko': '← 대화 목록', 'en': '← Conversations'},
    'turns2': {'ko': '${day(s.ended)} · ${s.turns}턴</div>`;', 'en': '${day(s.ended)} · ${s.turns} turns</div>`;'},
    'sess_rewrites': {'ko': '<h3>이 대화의 고쳐 쓰기</h3>', 'en': '<h3>Rewrites in this conversation</h3>'},
    'sess_misses': {'ko': '원하는 응답을 못 받은 곳 <span class="chip">', 'en': 'Where you didn\'t get what you wanted <span class="chip">'},
    'verdicts': {'ko': '항목별 판정</h3>', 'en': 'Verdict per habit</h3>'},
    'na': {'ko': '"해당 없음"', 'en': '"Not applicable"'},
    'causes': {'ko': '{prompt_gap: ["내 지시의 빈틈", "c-gap"], agent_error: ["에이전트 잘못", "c-agent"],\n  changed_mind: ["마음이 바뀜", "c-mind"], external: ["외부 요인", "c-ext"], unclassified: ["미분류", "c-ext"]}', 'en': '{prompt_gap: ["Gap in your prompt", "c-gap"], agent_error: ["Agent error", "c-agent"],\n  changed_mind: ["Changed your mind", "c-mind"], external: ["External limit", "c-ext"], unclassified: ["Unclassified", "c-ext"]}'},
    'signals': {'ko': '{correction: "바로잡음", repeat: "같은 말 반복", redo: "다시/되돌리기", mishap: "사고·손해", ask_back: "되물음", frustration: "답답함"}', 'en': '{correction: "Corrected", repeat: "Repeated yourself", redo: "Redo / undo", mishap: "Mishap", ask_back: "Agent asked back", frustration: "Frustration"}'},
    'miss_h': {'ko': '<h2>원하는 응답을 못 받은 곳 <span class="muted small">${tot}곳</span></h2>', 'en': '<h2>Missed responses <span class="muted small">${tot}</span></h2>'},
    'miss_note': {'ko': '짧은 지시라도 맥락으로 통했으면 문제 삼지 않습니다. 고쳐 쓰기는 <b>내 지시의 빈틈</b>에만 붙습니다.', 'en': 'Short prompts are fine when context carried the intent. Rewrites are given only for <b>gaps in your prompt</b>.'},
    'rule_cands': {'ko': '`규칙 후보 ${themes.length}`', 'en': '`Rule candidates ${themes.length}`'},
    'repeat_n': {'ko': '${m.refs.length}번 반복 · ${esc(m.where)}', 'en': 'repeated ${m.refs.length}× · ${esc(m.where)}'},
    'none_here': {'ko': '해당하는 곳이 없습니다', 'en': 'Nothing here'},
    'one_piece': {'ko': '<b>이 한 조각만 더했다면</b>', 'en': '<b>With the one missing piece</b>'},
    'prompt_turn': {'ko': '<b>지시 · turn ${m.turn}</b>', 'en': '<b>Prompt · turn ${m.turn}</b>'},
    'what_happened': {'ko': '무슨 일이 있었나</span>', 'en': 'What happened</span>'},
    'why_lbl': {'ko': '${m.cause === "prompt_gap" ? "빠진 것" : "내 지시 문제가 아닌 이유"}', 'en': '${m.cause === "prompt_gap" ? "Missing piece" : "Why it wasn\'t your prompt"}'},
    'no_misses': {'ko': '놓친 응답이 없습니다. LLM 채점(--judge claude/codex)으로 돌려야 원인까지 나뉩니다.', 'en': 'No missed responses. Causes are only classified with an LLM judge (--judge claude/codex).'},
    'back': {'ko': '← 목록</button>', 'en': '← List</button>'},
    'theme_meta': {'ko': '대화 ${new Set(m.refs.map(r => r.session)).size}곳에서 ${m.refs.length}번 빠짐 · 추천 위치: ${esc(m.where)}', 'en': 'Missing ${m.refs.length}× across ${new Set(m.refs.map(r => r.session)).size} conversations · put it in: ${esc(m.where)}'},
    'theme_rule': {'ko': '<b>규칙 파일에 이 한 줄을 넣어 두면 매번 말하지 않아도 됩니다</b>', 'en': "<b>Add this line to a rules file and you won't have to say it again</b>"},
    'theme_items': {'ko': '빠졌던 지시</h3>', 'en': 'Prompts that missed it</h3>'},
    'theme_badge': {'ko': '<b>반복되는 빈틈: ${esc(t.title)}</b>', 'en': '<b>Recurring gap: ${esc(t.title)}</b>'},
    'first_run': {'ko': '"아직 첫 회차입니다. 1~2주 뒤 agent-coach run 을 다시 돌리면 그 사이 대화만 채점해 변화가 쌓입니다."', 'en': '"This is your first run. Run agent-coach run again in a week or two; only the new conversations are graded and your progress builds up here."'},
    'versions': {'ko': '`회차마다 채점표 버전이 다릅니다(v${versions.join(", v")}). 새 항목은 이전 회차에 점수가 없습니다.` : `${runs.length}회차 기록`', 'en': '`Runs used different rubric versions (v${versions.join(", v")}). New habits have no score in earlier runs.` : `${runs.length} runs`'},
    'no_record': {'ko': '\'<div class="muted small">기록 없음</div>\'', 'en': '\'<div class="muted small">No data</div>\''},
    'spark_aria': {'ko': 'aria-label="회차별 점수"', 'en': 'aria-label="Score per run"'},
    'pts3': {'ko': '${x[0]}: ${x[1]}점</title>', 'en': '${x[0]}: ${x[1]}</title>'},
    's_overall': {'ko': '[["종합", null,', 'en': '[["Overall", null,'},
    's_gap': {'ko': '["놓친 응답 중 내 빈틈 비율(낮을수록 좋음)", null,', 'en': '["Share of misses that were prompt gaps (lower is better)", null,'},
}


TEMPLATE = r"""<!doctype html>
<html lang="{{html_lang}}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{{title}}
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
/* misses */
.stack{display:flex;height:10px;border-radius:99px;overflow:hidden;background:var(--surface2);margin:8px 0 6px;gap:2px}
.stack span{display:block;height:100%}
.c-gap{background:var(--accent)}.c-agent{background:var(--prev)}.c-mind{background:var(--grid)}.c-ext{background:var(--line)}
.keys{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--text2)}
.keys i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:baseline}
.seg{display:flex;gap:4px;flex-wrap:wrap;margin:10px 0}
.seg button{border:1px solid var(--line);background:var(--surface);border-radius:99px;padding:3px 10px;cursor:pointer;font-size:12px}
.seg button[aria-pressed="true"]{background:var(--text);color:var(--surface);border-color:var(--text)}
.theme{background:var(--warn-bg)}
.lbl{font-size:11px;font-weight:600;color:var(--text2)}
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
 <div class="kpi">{{overall}}<b id="kpi-score">–</b><span class="muted small">/100</span><span id="kpi-delta"></span></div>
 <div class="meta" id="meta"></div>
 <button class="iconbtn" id="theme" {{theme_btn}}>◐</button>
</header>
<nav class="tabs" role="tablist">
 <button role="tab" {{tab_overview}}/button>
 <button role="tab" {{tab_coach}}/button>
 <button role="tab" {{tab_misses}}/button>
 <button role="tab" {{tab_sessions}}/button>
 <button role="tab" {{tab_trend}}/button>
</nav>
<main>
 <section class="view" id="v-overview">
  <div class="card scroll">
   {{focus_h}}
   <ol class="focus" id="focus"></ol>
   <p class="small muted" id="best"></p>
   <div class="tiles" id="tiles"></div>
   <p class="small muted" id="about"></p>
  </div>
  <div class="card c-radar" style="display:flex;flex-direction:column">
   {{radar_h}}
   <div style="flex:1;min-height:0" id="radar"></div>
   <div class="legend" id="legend"></div>
  </div>
  <div class="card scroll c-dims">
   {{weak_h}}
   <ul class="barlist" id="ov-dims"></ul>
  </div>
 </section>

 <section class="view md" id="v-coach">
  <div class="card c-list">{{dims_h}}<ul class="barlist list scroll" id="coach-list"></ul></div>
  <div class="card c-detail detail" id="coach-detail"></div>
 </section>

 <section class="view md" id="v-misses">
  <div class="card c-list">
   <div id="miss-sum"></div>
   <div class="seg" id="miss-filter"></div>
   <ul class="slist list scroll" id="miss-list"></ul>
  </div>
  <div class="card c-detail detail" id="miss-detail"></div>
 </section>

 <section class="view md" id="v-sessions">
  <div class="card c-list">
   <div class="toolbar"><input id="q" type="search" {{search_ph}}><select id="filter"></select></div>
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
const pill = v => `<span class="pill ${v == null ? "pn" : "p" + v}">${v == null ? "–" : {{pill}}[v]}</span>`;
const store = {get(k){try{return localStorage.getItem(k)}catch(e){return null}}, set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};

/* ---------- header ---------- */
$("#kpi-score").textContent = cur.overall ?? "–";
$("#kpi-delta").innerHTML = prev && prev.rubric_version === cur.rubric_version ? delta(cur.overall, prev.overall) : "";
$("#meta").textContent = {{meta}};
const theme = store.get("ac-theme"); if (theme) document.documentElement.dataset.theme = theme;
$("#theme").onclick = () => {
  const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "light" : "dark"; store.set("ac-theme", document.documentElement.dataset.theme);
};

/* ---------- routing ---------- */
const views = ["overview", "coach", "misses", "sessions", "trend"];
function go(tab, arg, push = true) {
  if (!views.includes(tab)) tab = "overview";
  document.querySelectorAll("nav.tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("on", v.id === "v-" + tab));
  if (tab === "coach") showDim(arg || state.dim, !!arg);
  if (tab === "sessions") showSession(arg || state.sess, !!arg);
  if (tab === "misses") showMiss(arg || state.miss, !!arg);
  if (push) history.replaceState(null, "", "#" + tab + (arg ? "/" + arg : ""));
}
document.querySelectorAll("nav.tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll(".md").forEach(m => m.classList.remove("showing")); go(b.dataset.tab);
});
const state = {dim: null, sess: null, miss: null, cause: "prompt_gap"};

/* ---------- overview ---------- */
const ranked = dims.filter(d => sc(d.id) != null).sort((a, b) => sc(a.id) - sc(b.id));
const unscored = dims.filter(d => sc(d.id) == null);
$("#focus").innerHTML = ranked.slice(0, 3).map(d =>
  `<li><button data-dim="${d.id}">${esc(d.name)}</button> {{pts1}}<div class="small muted">${esc(d.summary)}</div></li>`).join("");
const best = ranked[ranked.length - 1];
$("#best").innerHTML = best ? {{best}} : "";
const nCoach = sessions.reduce((a, s) => a + (s.coaching || []).length, 0);
const MS = D.current.misses || {total: 0, by_cause: {}, themes: []};
const nGap = (MS.by_cause || {}).prompt_gap || 0;
$("#tiles").innerHTML = `<button data-go="sessions"><b>${sessions.length}</b>{{tile1}}</button>
 <button data-go="coach"><b>${nCoach}</b>{{tile2}}</button>
 <button data-go="misses"><b>${nGap}<small class="muted" style="font-size:13px"> / ${MS.total}</small></b>{{tile3}}</button>`;
document.querySelectorAll("[data-go]").forEach(b => b.onclick = () => go(b.dataset.go));
$("#about").innerHTML =`${esc(D.rubric.title)}. {{about}}`;
const barItem = d => {
  const v = sc(d.id), n = cur.dimensions[d.id] || {};
  return `<li data-dim="${d.id}"><span class="nm">${esc(d.name)} <span class="small muted">{{nconv}}</span></span>
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
  let s = `<svg viewBox="0 0 ${W} ${H}" class="radar" role="img" {{radar_aria}}>`;
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
    s += `<circle class="dot" data-dim="${d.id}" cx="${x}" cy="${y}" r="5"><title>{{pts2}}</circle>`; });
  $("#radar").innerHTML = s + "</svg>";
  $("#legend").innerHTML = `<span><i style="background:var(--accent)"{{legend_cur}}</span>` +
    (prev ? `<span><i style="background:var(--prev)"{{legend_prev}}</span>` : "");
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
  let h = `<button class="iconbtn back" data-back>{{back_dims}}</button>
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap">
   <div><h2 style="font-size:18px;margin:0">${esc(d.name)}</h2><div class="muted">${esc(d.summary)}</div></div>
   <div><span class="big" style="font-size:40px">${v.score ?? "–"}</span>${delta(v.score, pv)}</div></div>
  <div class="small muted" style="margin:6px 0 4px">{{dim_counts}}</div>`;
  if (ex.length) {
    h += `<h3 style="margin-top:14px">{{rewrites_h}} class="chip">${ex.length}</span></h3>`;
    h += ex.map(c => `<div class="coach"><div class="ex"><div class="before">{{you_wrote}}${esc(c.original)}</div>
      <div class="after">{{better}}${esc(c.better)}</div></div><div class="why">${esc(c.why)}</div>
      <div class="sess"><a href="#sessions/${esc(c.s.id)}" data-sess="${esc(c.s.id)}">${sessLine(c.s)}</a></div></div>`).join("");
  } else if (d.example) {
    h += `<h3 style="margin-top:14px">{{guide_ex_h}}<div class="ex"><div class="before">{{instead}}${esc(d.example.before)}</div><div class="after">{{try}}${esc(d.example.after)}</div></div>`;
  }
  h += `<details ${ex.length ? "" : "open"}><summary>{{guide_n}}</summary>` + d.guide.map(g => {
    const src = D.rubric.sources[g.source] || {}; return `<div class="guide">${esc(g.quote)}<br><a href="${esc(src.url)}" target="_blank" rel="noopener">${esc(src.title)} · ${esc(g.section)}</a></div>`;
  }).join("") + `</details>`;
  if (ms.length) h += `<details><summary>{{missed_n}}` +
    ms.map(m => `<tr><td><a href="#sessions/${esc(m.s.id)}" data-sess="${esc(m.s.id)}">${esc(m.s.task_summary)}</a><div class="sess">${day(m.s.ended)} · ${esc(m.s.project)}</div></td><td>${esc(m.note)}${m.excerpt ? `<div class="sess">“${esc(m.excerpt)}”</div>` : ""}</td></tr>`).join("") + `</table></details>`;
  $("#coach-detail").innerHTML = h; $("#coach-detail").scrollTop = 0;
  if (open) $("#v-coach").classList.add("showing");
}

/* ---------- sessions ---------- */
$("#filter").innerHTML = `{{all_dims}}` + dims.map(d => `<option value="${d.id}">{{missed_opt}}`).join("");
const markOf = v => v == null ? "·" : ["✗", "△", "○"][v];
function listSessions() {
  const q = $("#q").value.trim().toLowerCase(), f = $("#filter").value;
  const rows = sessions.filter(s => (!q || (s.task_summary + " " + s.project).toLowerCase().includes(q)) &&
    (!f || (s.dimensions[f] || {}).score === 0));
  $("#sess-list").innerHTML = rows.map(s => `<li data-id="${esc(s.id)}"><div>${esc(s.task_summary)}</div>
    <div class="sess">${day(s.ended)} · ${esc(SRC[s.source] || s.source)} {{turns1}} title="${dims.map(d => d.short).join(" ")}">${dims.map(d => markOf((s.dimensions[d.id] || {}).score)).join("")}</div></li>`).join("")
    || `<li class="muted">{{no_match}}</li>`;
  document.querySelectorAll("#sess-list li[data-id]").forEach(li => li.setAttribute("aria-current", li.dataset.id === state.sess));
}
$("#q").oninput = listSessions; $("#filter").onchange = listSessions;
$("#sess-list").addEventListener("click", e => { const li = e.target.closest("li[data-id]"); if (li) go("sessions", li.dataset.id); });
document.addEventListener("click", e => { const a = e.target.closest("[data-sess]"); if (a) { e.preventDefault(); go("sessions", a.dataset.sess); } });
function showSession(id, open) {
  listSessions();
  const s = sessions.find(x => x.id === id) || sessions[0]; if (!s) { $("#sess-detail").innerHTML = '<p class="muted">{{no_sess}}</p>'; return; }
  state.sess = s.id;
  document.querySelectorAll("#sess-list li[data-id]").forEach(li => li.setAttribute("aria-current", li.dataset.id === s.id));
  let h = `<button class="iconbtn back" data-back>{{back_sess}}</button>
   <h2 style="font-size:17px;margin:0">${esc(s.task_summary)}</h2>
   <div class="sess" style="margin-bottom:10px">${esc(SRC[s.source] || s.source)} · ${esc(s.project)} · ${day(s.started)} ~ {{turns2}}
  if ((s.coaching || []).length) h += `{{sess_rewrites}}` + s.coaching.map(c => {
    const d = dims.find(x => x.id === c.dimension) || {}; return `<div class="coach"><span class="chip">${esc(d.name || c.dimension)}</span>
    <div class="ex"><div class="before">{{you_wrote}}${esc(c.original)}</div><div class="after">{{better}}${esc(c.better)}</div></div><div class="why">${esc(c.why)}</div></div>`; }).join("");
  const sm = misses.filter(m => m.s.id === s.id);
  if (sm.length) h += `<h3 style="margin-top:14px">{{sess_misses}}${sm.length}</span></h3>` + sm.map(m => missBlock(m, false)).join("");
  h += `<h3 style="margin-top:14px">{{verdicts}}` + dims.map(d => { const v = s.dimensions[d.id] || {};
    return `<div class="score-row"><a href="#coach/${d.id}" data-dim="${d.id}">${esc(d.name)}</a>${pill(v.score)}<div>${esc(v.note || (v.score == null ? {{na}} : ""))}${v.excerpt ? `<div class="sess">turn ${v.evidence_turn}: “${esc(v.excerpt)}”</div>` : ""}</div></div>`; }).join("");
  $("#sess-detail").innerHTML = h; $("#sess-detail").scrollTop = 0;
  if (open) $("#v-sessions").classList.add("showing");
}
document.addEventListener("click", e => { if (e.target.closest("[data-back]")) document.querySelectorAll(".md").forEach(m => m.classList.remove("showing")); });

/* ---------- misses ---------- */
const CAUSE = {{causes}};
const SIGNAL = {{signals}};
const misses = [];
sessions.forEach(s => (s.misses || []).forEach((m, i) => misses.push({...m, s, key: s.id + ":" + i})));
const themes = (MS.themes || []).map((t, i) => ({...t, key: "theme:" + i}));
(function summary() {
  const bc = MS.by_cause || {}, tot = MS.total || 0;
  const order = ["prompt_gap", "agent_error", "changed_mind", "external", "unclassified"].filter(k => bc[k]);
  $("#miss-sum").innerHTML = `{{miss_h}}
   <div class="stack">${order.map(k => `<span class="${CAUSE[k][1]}" style="width:${bc[k] / tot * 100}%" title="${CAUSE[k][0]} ${bc[k]}"></span>`).join("")}</div>
   <div class="keys">${order.map(k => `<span><i class="${CAUSE[k][1]}"></i>${CAUSE[k][0]} ${bc[k]}</span>`).join("")}</div>
   <p class="small muted" style="margin:8px 0 0">{{miss_note}}</p>`;
  const opts = [["themes", {{rule_cands}}], ...order.map(k => [k, `${CAUSE[k][0]} ${bc[k]}`])];
  if (!themes.length) opts.shift();
  if (!opts.find(o => o[0] === state.cause)) state.cause = opts.length ? opts[0][0] : "prompt_gap";
  $("#miss-filter").innerHTML = opts.map(([k, l]) => `<button data-cause="${k}" aria-pressed="${k === state.cause}">${esc(l)}</button>`).join("");
  $("#miss-filter").onclick = e => { const b = e.target.closest("[data-cause]"); if (!b) return; state.cause = b.dataset.cause;
    document.querySelectorAll("#miss-filter button").forEach(x => x.setAttribute("aria-pressed", x === b)); state.miss = null; showMiss(null, false); };
})();
function listMisses() {
  const items = state.cause === "themes" ? themes : misses.filter(m => m.cause === state.cause);
  $("#miss-list").innerHTML = items.map(m => m.key.startsWith("theme:")
    ? `<li data-miss="${m.key}"><div><b>${esc(m.title)}</b></div><div class="sess">{{repeat_n}}</div></li>`
    : `<li data-miss="${esc(m.key)}"><div>${esc(m.original)}</div><div class="sess">${esc(SIGNAL[m.signal] || m.signal)} · ${day(m.s.ended)} · ${esc(m.s.project)}</div></li>`).join("")
    || `<li class="muted">{{none_here}}</li>`;
  return items;
}
$("#miss-list").addEventListener("click", e => { const li = e.target.closest("li[data-miss]"); if (li) go("misses", li.dataset.miss); });
function missBlock(m, withSession = true) {
  const c = CAUSE[m.cause] || CAUSE.unclassified;
  let h = `<div class="coach"><span class="chip"><i class="${c[1]}" style="display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px"></i>${c[0]}</span><span class="chip">${esc(SIGNAL[m.signal] || m.signal)}</span>`;
  if (m.better) h += `<div class="ex"><div class="before">{{you_wrote_m}}${esc(m.original)}</div><div class="after">{{one_piece}}${esc(m.better)}</div></div>`;
  else h += `<div class="ex" style="grid-template-columns:1fr"><div class="before" style="background:var(--surface2)">{{prompt_turn}}${esc(m.original)}</div></div>`;
  h += `<div class="why"><span class="lbl">{{what_happened}} ${esc(m.what_went_wrong)}</div>`;
  if (m.why) h += `<div class="why"><span class="lbl">{{why_lbl}}</span> ${esc(m.why)}</div>`;
  if (withSession) h += `<div class="sess"><a href="#sessions/${esc(m.s.id)}" data-sess="${esc(m.s.id)}">${sessLine(m.s)}</a></div>`;
  return h + `</div>`;
}
function showMiss(key, open) {
  const items = listMisses();
  const m = items.find(x => x.key === key) || items[0];
  if (!m) { $("#miss-detail").innerHTML = '<p class="muted">{{no_misses}}</p>'; return; }
  state.miss = m.key;
  document.querySelectorAll("#miss-list li[data-miss]").forEach(li => li.setAttribute("aria-current", li.dataset.miss === m.key));
  let h = `<button class="iconbtn back" data-back>{{back}}`;
  if (m.key.startsWith("theme:")) {
    h += `<h2 style="font-size:17px;margin:0">${esc(m.title)}</h2><div class="sess">{{theme_meta}}</div>
     <div class="ex" style="grid-template-columns:1fr"><div class="after">{{theme_rule}}${esc(m.rule)}</div></div>
     <h3 style="margin-top:14px">{{theme_items}}` +
     m.refs.map(r => misses.find(x => x.s.id === r.session && x.turn === r.turn)).filter(Boolean).map(x => missBlock(x)).join("");
  } else {
    h += `<h2 style="font-size:16px;margin:0 0 4px">${esc(m.s.task_summary)}</h2>` + missBlock(m);
    const t = themes.find(t => t.refs.some(r => r.session === m.s.id && r.turn === m.turn));
    if (t) h += `<div class="ex" style="grid-template-columns:1fr"><div class="theme">{{theme_badge}}${esc(t.rule)}</div></div>`;
  }
  $("#miss-detail").innerHTML = h; $("#miss-detail").scrollTop = 0;
  if (open) $("#v-misses").classList.add("showing");
}

/* ---------- trend ---------- */
const versions = [...new Set(runs.map(r => r.rubric_version))];
$("#trend-note").textContent = runs.length < 2
  ? {{first_run}}
  : versions.length > 1 ? {{versions}};
function spark(pts) {
  const p = pts.filter(x => x[1] != null); if (!p.length) return {{no_record}};
  const W = 200, H = 56, pad = 8, xs = p.map((_, i) => pad + (W - 2 * pad) * (p.length > 1 ? i / (p.length - 1) : .5)), ys = p.map(x => H - pad - (H - 2 * pad) * x[1] / 100);
  let s = `<svg viewBox="0 0 ${W} ${H}" class="spark" role="img" {{spark_aria}}><line class="grid" x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}"/>`;
  if (p.length > 1) s += `<polyline class="trend" points="${xs.map((x, i) => x + "," + ys[i]).join(" ")}"/>`;
  p.forEach((x, i) => s += `<circle class="dot" cx="${xs[i]}" cy="${ys[i]}" r="4"><title>{{pts3}}</circle>`);
  return s + "</svg>";
}
const series = {{s_overall}} runs.map(r => [day(r.created), r.overall])],
  {{s_gap}} runs.map(r => [day(r.created), r.gap_share])]].concat(dims.map(d => [d.name, d.id, runs.map(r => [day(r.created), (r.dimensions[d.id] || {}).score])]));
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
