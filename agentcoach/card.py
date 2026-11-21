"""Share card for the weekly score: one self-contained HTML file with an animated SVG and a 'save PNG' button.

The tier sets the colours and the effects: a light sweep for everyone, twinkling stars from Platinum,
and a confetti burst from Gold. The PNG export is a clean still frame with the final numbers.
"""
from __future__ import annotations

import html

from .rank import TIERS, tier_of

L = {
    "ko": {"title": "이번 주 AI 지시 점수", "quality": "품질", "convos": "대화", "bonus": "보너스",
           "best": "가장 잘한 습관", "up": "지난주보다", "save": "PNG로 저장", "copy": "공유 문구 복사",
           "to_next": "{tier}까지 {gap}점", "top": "최고 티어",
           "share": "내 Claude Code·Codex 대화로 채점한 이번 주 AI 지시 점수: {score}점, {tier} 티어. 너도 재 봐 →",
           "not_eligible": "대화 {min}개 이상 채점되면 순위에 오릅니다", "tiers": "티어 기준"},
    "en": {"title": "Weekly prompting score", "quality": "Quality", "convos": "Convos", "bonus": "Bonus",
           "best": "Strongest habit", "up": "vs last week", "save": "Save PNG", "copy": "Copy share text",
           "to_next": "{gap} to {tier}", "top": "Top tier",
           "share": "My weekly prompting score from my own Claude Code / Codex history: {score}, {tier} tier. Measure yours →",
           "not_eligible": "Grade at least {min} conversations to be ranked", "tiers": "Tiers"},
}
REPO_URL = "github.com/1017toa/agent-coach"


def _stars(n: int) -> str:
    # fixed positions so the card looks the same every time
    pts = [(820, 90), (1040, 150), (560, 70), (700, 60), (1165, 300), (640, 560), (790, 300), (1150, 90)]
    out = []
    for i, (x, y) in enumerate(pts[:n]):
        r = 5 + (i % 3) * 2
        out.append(f'<path class="star" style="animation-delay:{i * 0.35:.2f}s" transform="translate({x} {y})" '
                   f'd="M0 -{r * 2} L{r * .5} -{r * .5} L{r * 2} 0 L{r * .5} {r * .5} L0 {r * 2} L-{r * .5} {r * .5} '
                   f'L-{r * 2} 0 L-{r * .5} -{r * .5} Z" fill="#fff"/>')
    return "".join(out)


def render_card(p: dict, rubric: dict, lang: str = "en", min_convos: int = 3) -> str:
    t = L.get(lang, L["en"])
    e = lambda s: html.escape(str(s))  # noqa: E731
    names = {d["id"]: d["name"] for d in rubric["dimensions"]}
    habits = sorted(((v, k) for k, v in (p.get("habits") or {}).items() if v is not None), reverse=True)
    best = f"{names.get(habits[0][1], habits[0][1])} {habits[0][0]}" if habits else "-"
    imp = p.get("improvement")
    imp_txt = f"{t['up']} {'+' if imp >= 0 else ''}{imp}" if imp is not None else ""
    score = p.get("score")
    score_txt = "-" if score is None else f"{score:.0f}"
    tr = tier_of(score)
    tname = tr["ko"] if lang == "ko" else tr["en"]
    nname = tr["next_ko"] if lang == "ko" else tr["next_en"]
    next_txt = t["to_next"].format(tier=nname, gap=tr["gap"]) if nname else t["top"]
    league = f" · {e(p['league'])}" if p.get("league") else ""
    elig = "" if p.get("conversations", 0) >= min_convos else t["not_eligible"].format(min=min_convos)
    share = t["share"].format(score=score_txt, tier=tname) + f" https://{REPO_URL}"
    rank_i = [x[1] for x in TIERS].index(tr["id"])          # 0 = master … 6 = iron
    stars = _stars({0: 8, 1: 6, 2: 4}.get(rank_i, 0))
    confetti = "true" if rank_i <= 3 else "false"            # gold and above
    bar_w = 420 * tr["progress"]
    svg = f"""<svg id="card" xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<defs>
 <linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{tr['from']}"/><stop offset="1" stop-color="{tr['to']}"/></linearGradient>
 <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
 <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <clipPath id="clip"><rect width="1200" height="630" rx="36"/></clipPath>
</defs>
<g clip-path="url(#clip)">
 <rect width="1200" height="630" fill="url(#g)"/>
 <circle cx="1080" cy="80" r="260" fill="#fff" opacity=".07"/><circle cx="160" cy="640" r="220" fill="#000" opacity=".08"/>
 <g class="fx">{stars}</g>
 <rect class="fx sweep" x="-400" y="-100" width="260" height="830" fill="url(#shine)" transform="skewX(-18)"/>
</g>
<g font-family="Segoe UI, Apple SD Gothic Neo, Malgun Gothic, Noto Sans KR, sans-serif" fill="#fff">
 <text x="72" y="104" font-size="32" opacity=".88">{e(t['title'])} · {e(p.get('week', ''))}{league}</text>
 <text x="72" y="178" font-size="52" font-weight="700">{e(p.get('nickname') or 'anonymous')}</text>
 <text id="score" x="72" y="398" font-size="210" font-weight="800" data-final="{e(score_txt)}">{e(score_txt)}</text>
 <text x="72" y="462" font-size="30" opacity=".92">{e(t['quality'])} {e(p.get('quality', '-'))} · {e(t['convos'])} {e(p.get('conversations', 0))} · {e(t['bonus'])} ×{float(p.get('bonus') or 1):.2f}</text>
 <g transform="translate(940 250)">
  <polygon points="0,-118 102,-59 102,59 0,118 -102,59 -102,-59" fill="#fff" fill-opacity=".16" stroke="{tr['accent']}" stroke-width="6" filter="url(#glow)" class="badge"/>
  <polygon points="0,-90 78,-45 78,45 0,90 -78,45 -78,-45" fill="{tr['to']}" fill-opacity=".55"/>
  <text y="22" font-size="64" font-weight="800" text-anchor="middle" fill="{tr['accent']}">{e(tr['en'][0])}</text>
  <text y="160" font-size="40" font-weight="800" text-anchor="middle">{e(tname)}</text>
 </g>
 <text x="72" y="520" font-size="24" opacity=".85">{e(next_txt)}</text>
 <rect x="72" y="534" width="420" height="12" rx="6" fill="#fff" opacity=".22"/>
 <rect class="bar" x="72" y="534" width="{bar_w:.0f}" height="12" rx="6" fill="{tr['accent']}"/>
 <text x="1128" y="470" font-size="26" text-anchor="end" opacity=".85">{e(t['best'])}: {e(best)}</text>
 <text x="1128" y="510" font-size="28" text-anchor="end" fill="{tr['accent']}">{e(imp_txt)}</text>
 <text x="72" y="596" font-size="24" opacity=".8">agent-coach · {REPO_URL}</text>
 <text x="1128" y="596" font-size="22" text-anchor="end" fill="{tr['accent']}">{e(elig)}</text>
</g></svg>"""
    legend = " · ".join(f"{(ko if lang == 'ko' else en)} {lo}+" for lo, _, ko, en, _, _ in reversed(TIERS))
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>agent-coach · {e(tname)} · {e(p.get('week', ''))}</title>
<style>
body{{margin:0;padding:24px;background:#101014;color:#e8e8ee;font-family:system-ui,"Malgun Gothic",sans-serif;display:flex;flex-direction:column;align-items:center;gap:16px;min-height:100vh;box-sizing:border-box}}
.wrap{{position:relative;max-width:100%}}#fx{{position:absolute;inset:0;pointer-events:none;width:100%;height:100%}}
svg{{display:block;max-width:100%;height:auto;border-radius:18px;box-shadow:0 0 0 2px {tr['accent']}55,0 18px 60px {tr['from']}66;animation:pop .7s cubic-bezier(.2,1.4,.4,1) both}}
@keyframes pop{{from{{transform:scale(.85) rotate(-2deg);opacity:0}}to{{transform:none;opacity:1}}}}
.sweep{{animation:sweep 3.2s ease-in-out .8s infinite}}@keyframes sweep{{0%{{transform:skewX(-18deg) translateX(0)}}60%,100%{{transform:skewX(-18deg) translateX(1900px)}}}}
.star{{transform-box:fill-box;transform-origin:center;animation:tw 1.8s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:.15;scale:.6}}50%{{opacity:1;scale:1.1}}}}
.badge{{animation:pulse 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}@keyframes pulse{{50%{{scale:1.04}}}}
.bar{{animation:grow 1.4s cubic-bezier(.2,.8,.2,1) .4s both;transform-box:fill-box;transform-origin:left}}@keyframes grow{{from{{scale:0 1}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
button{{font:inherit;padding:10px 18px;border-radius:10px;border:0;background:{tr['from']};color:#fff;cursor:pointer}}
.row{{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}}p{{max-width:760px;text-align:center;margin:0}}.legend{{opacity:.6;font-size:14px}}
</style></head><body>
<div class="wrap">{svg}<canvas id="fx"></canvas></div>
<div class="row"><button id="png">{e(t['save'])}</button><button id="copy">{e(t['copy'])}</button></div>
<p id="txt">{e(share)}</p>
<p class="legend">{e(t['tiers'])}: {e(legend)}</p>
<script>
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const sc = document.getElementById("score"), fin = parseFloat(sc.dataset.final);
if (!reduce && !isNaN(fin)) {{ const t0 = performance.now();
  const step = now => {{ const k = Math.min(1, (now - t0) / 1100); sc.textContent = Math.round(fin * (1 - Math.pow(1 - k, 3)));
    if (k < 1) requestAnimationFrame(step); else sc.textContent = sc.dataset.final; }}; requestAnimationFrame(step); }}
if ({confetti} && !reduce) {{
  const c = document.getElementById("fx"), x = c.getContext("2d"), r = c.getBoundingClientRect();
  c.width = r.width; c.height = r.height;
  const cols = ["{tr['accent']}", "#ffffff", "{tr['from']}", "#ffd43b"];
  const ps = Array.from({{length: 140}}, () => ({{x: c.width * .78, y: c.height * .4, vx: (Math.random() - .5) * 14,
    vy: -Math.random() * 13 - 3, s: 4 + Math.random() * 6, a: Math.random() * 6, c: cols[Math.floor(Math.random() * cols.length)]}}));
  let n = 0; (function f() {{ x.clearRect(0, 0, c.width, c.height);
    for (const p of ps) {{ p.vy += .35; p.x += p.vx; p.y += p.vy; p.a += .2; x.save(); x.translate(p.x, p.y); x.rotate(p.a);
      x.fillStyle = p.c; x.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); x.restore(); }}
    if (++n < 160) requestAnimationFrame(f); else x.clearRect(0, 0, c.width, c.height); }})();
}}
document.getElementById("png").onclick = () => {{
  const clone = document.getElementById("card").cloneNode(true);
  clone.querySelectorAll(".fx.sweep").forEach(n => n.remove());
  clone.querySelector("#score").textContent = sc.dataset.final;
  const img = new Image();
  img.onload = () => {{ const cv = document.createElement("canvas"); cv.width = 1200; cv.height = 630;
    cv.getContext("2d").drawImage(img, 0, 0); const a = document.createElement("a");
    a.download = "agent-coach-{e(p.get('week', 'week'))}.png"; a.href = cv.toDataURL("image/png"); a.click(); }};
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(clone));
}};
document.getElementById("copy").onclick = () => navigator.clipboard.writeText(document.getElementById("txt").textContent);
</script></body></html>"""
