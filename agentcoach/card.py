"""Share card for the weekly score: one self-contained HTML file with an SVG and a 'save PNG' button."""
from __future__ import annotations

import html

L = {
    "ko": {"title": "이번 주 AI 지시 점수", "quality": "품질", "convos": "대화", "bonus": "활동 보너스",
           "best": "가장 잘한 습관", "up": "지난주보다", "save": "PNG로 저장", "copy": "공유 문구 복사",
           "share": "내 Claude Code·Codex 대화로 채점한 이번 주 AI 지시 점수: {score}점. 너도 재 봐 →",
           "not_eligible": "대화 {min}개 이상 채점되면 순위에 오릅니다"},
    "en": {"title": "Weekly prompting score", "quality": "Quality", "convos": "Conversations", "bonus": "Activity bonus",
           "best": "Strongest habit", "up": "vs last week", "save": "Save PNG", "copy": "Copy share text",
           "share": "My weekly prompting score from my own Claude Code / Codex history: {score}. Measure yours →",
           "not_eligible": "Grade at least {min} conversations to be ranked"},
}
REPO_URL = "github.com/1017toa/agent-coach"


def render_card(p: dict, rubric: dict, lang: str = "en", min_convos: int = 3) -> str:
    t = L.get(lang, L["en"])
    e = lambda s: html.escape(str(s))  # noqa: E731
    names = {d["id"]: d["name"] for d in rubric["dimensions"]}
    habits = sorted(((v, k) for k, v in (p.get("habits") or {}).items() if v is not None), reverse=True)
    best = f"{names.get(habits[0][1], habits[0][1])} {habits[0][0]}" if habits else "-"
    imp = p.get("improvement")
    imp_txt = f"{t['up']} {'+' if imp >= 0 else ''}{imp}" if imp is not None else ""
    score = p.get("score")
    score_txt = "-" if score is None else (f"{score:.0f}" if score >= 10 else f"{score}")
    league = f" · {e(p['league'])}" if p.get("league") else ""
    elig = "" if p.get("conversations", 0) >= min_convos else t["not_eligible"].format(min=min_convos)
    share = t["share"].format(score=score_txt) + f" https://{REPO_URL}"
    svg = f"""<svg id="card" xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b5bdb"/><stop offset="1" stop-color="#7048e8"/></linearGradient></defs>
<rect width="1200" height="630" rx="36" fill="url(#g)"/>
<g font-family="Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif" fill="#fff">
<text x="72" y="110" font-size="34" opacity=".85">{e(t['title'])} · {e(p.get('week', ''))}{league}</text>
<text x="72" y="190" font-size="54" font-weight="700">{e(p.get('nickname') or 'anonymous')}</text>
<text x="72" y="410" font-size="220" font-weight="800">{e(score_txt)}</text>
<text x="72" y="480" font-size="32" opacity=".9">{e(t['quality'])} {e(p.get('quality', '-'))} · {e(t['convos'])} {e(p.get('conversations', 0))} · {e(t['bonus'])} ×{float(p.get('bonus') or 1):.2f}</text>
<text x="1128" y="330" font-size="30" text-anchor="end" opacity=".85">{e(t['best'])}</text>
<text x="1128" y="378" font-size="38" font-weight="700" text-anchor="end">{e(best)}</text>
<text x="1128" y="430" font-size="34" text-anchor="end" fill="#ffd43b">{e(imp_txt)}</text>
<text x="72" y="568" font-size="28" opacity=".8">agent-coach · {REPO_URL}</text>
<text x="1128" y="568" font-size="26" text-anchor="end" fill="#ffd43b">{e(elig)}</text>
</g></svg>"""
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>agent-coach · {e(p.get('week', ''))}</title>
<style>body{{margin:0;padding:24px;background:#f4f4f6;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;gap:16px}}
svg{{max-width:100%;height:auto;border-radius:18px;box-shadow:0 8px 30px #0002}}button{{font:inherit;padding:10px 18px;border-radius:10px;border:0;background:#3b5bdb;color:#fff;cursor:pointer}}
.row{{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}}p{{max-width:760px;color:#333;text-align:center}}</style></head><body>
{svg}
<div class="row"><button id="png">{e(t['save'])}</button><button id="copy">{e(t['copy'])}</button></div>
<p id="txt">{e(share)}</p>
<script>
document.getElementById("png").onclick = () => {{
  const s = new XMLSerializer().serializeToString(document.getElementById("card"));
  const img = new Image();
  img.onload = () => {{ const c = document.createElement("canvas"); c.width = 1200; c.height = 630;
    c.getContext("2d").drawImage(img, 0, 0); const a = document.createElement("a");
    a.download = "agent-coach-{e(p.get('week', 'week'))}.png"; a.href = c.toDataURL("image/png"); a.click(); }};
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(s);
}};
document.getElementById("copy").onclick = () => navigator.clipboard.writeText(document.getElementById("txt").textContent);
</script></body></html>"""
