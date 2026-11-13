"""Language selection and CLI messages (Korean and English)."""
from __future__ import annotations

import locale
import os

SUPPORTED = ("en", "ko")


def detect_lang() -> str:
    """AGENT_COACH_LANG wins; otherwise follow the OS locale; default English."""
    env = os.environ.get("AGENT_COACH_LANG", "").lower()
    if env in SUPPORTED:
        return env
    candidates = [os.environ.get(k, "") for k in ("LC_ALL", "LC_MESSAGES", "LANG")]
    try:
        candidates.append(locale.getlocale()[0] or "")
    except ValueError:
        pass
    for c in candidates:
        c = c.lower()
        if c.startswith("ko") or "korean" in c:
            return "ko"
    return "en"


M = {
    "bad_source": {"en": "Unknown source: {bad} (choose from claude, codex)",
                   "ko": "알 수 없는 source: {bad} (claude, codex 중에서)"},
    "all_time": {"en": "all time", "ko": "전체"},
    "scan_head": {"en": "Window: since {since}  ·  {n} conversations",
                  "ko": "기간: {since} 이후  ·  대화 {n}개"},
    "scan_tail": {"en": "{turns} prompts you typed. Run `agent-coach run` to grade them (up to {max} conversations by default).",
                  "ko": "사람이 쓴 지시 {turns}개. `agent-coach run` 으로 채점합니다 (기본 최대 {max}개 대화)."},
    "nothing": {"en": "No conversations to grade. Widen the window with --days 30 or --all.",
                "ko": "채점할 대화가 없습니다. --days 30 이나 --all 로 기간을 넓혀 보세요."},
    "grading": {"en": "Grading {k} of {n} conversations · judge: {judge}",
                "ko": "대화 {n}개 중 {k}개를 채점합니다 · 채점기: {judge}"},
    "done": {"en": "done", "ko": "완료"},
    "fallback": {"en": "failed, using keyword scoring", "ko": "실패, 키워드 채점으로 대체"},
    "all_failed": {"en": "Every LLM grading call failed; saving keyword scores only. Use --verbose to see why.",
                   "ko": "LLM 채점이 모두 실패해 키워드 채점 결과만 저장합니다. --verbose 로 원인을 확인하세요."},
    "grouping": {"en": "Grouping prompt gaps that keep coming back…", "ko": "반복되는 지시 빈틈을 묶는 중…"},
    "result": {"en": "Overall {overall} · {gaps} of {total} missed responses were gaps in your prompt\nRun saved {path}\nReport {out}",
               "ko": "종합 {overall}점 · 놓친 응답 {total}곳 중 내 지시 빈틈 {gaps}곳\n기록 {path}\n리포트 {out}"},
    "no_runs": {"en": "No runs yet. Run `agent-coach run` first.",
                "ko": "아직 채점 기록이 없습니다. 먼저 `agent-coach run` 을 실행하세요."},
    "no_history": {"en": "No runs yet", "ko": "기록 없음"},
    "hist_head": {"en": ("Date", "Overall", "Convos", "Judge"), "ko": ("날짜", "종합", "대화", "채점기")},
    "desc": {"en": "Coach how you direct Claude Code and Codex, graded against the official guides using your own local transcripts.",
             "ko": "Claude Code·Codex 대화 기록으로 공식 가이드 기준 지시 습관을 코칭합니다."},
    "h_rubric": {"en": "Rubric JSON path (default: built-in, grounded in the official guides)",
                 "ko": "채점표 JSON 경로 (기본: 공식 가이드 기반)"},
    "h_source": {"en": "Which tools to read: claude,codex (default both)", "ko": "claude,codex 중 선택 (기본 둘 다)"},
    "h_days": {"en": "Last N days (default: since the previous run; 14 days on the first run)",
               "ko": "최근 N일 (기본: 지난 채점 이후, 첫 회는 14일)"},
    "h_all": {"en": "No time window", "ko": "기간 제한 없이 전체"},
    "h_sdk": {"en": "Also include scripted `claude -p` / `codex exec` conversations",
              "ko": "스크립트로 돌린 claude -p / codex exec 대화도 포함"},
    "h_max": {"en": "Max conversations to grade (default 20)", "ko": "채점할 최대 대화 수 (기본 20)"},
    "h_lang": {"en": "Language for the report and coaching (default: from your OS locale)",
               "ko": "리포트와 코칭 언어 (기본: OS 언어 설정)"},
    "h_scan": {"en": "Preview which conversations would be graded (no model calls)",
               "ko": "채점 대상 대화를 미리 봅니다 (모델 호출 없음)"},
    "h_run": {"en": "Grade, save the run and open the report", "ko": "채점하고 기록을 남긴 뒤 리포트를 엽니다"},
    "h_judge": {"en": "Judge (default auto: claude → codex → keywords)", "ko": "채점기 (기본 auto: claude → codex → 키워드)"},
    "h_model": {"en": "Model for the judge (e.g. sonnet, haiku, gpt-5.5)", "ko": "채점에 쓸 모델 (예: sonnet, haiku, gpt-5.5)"},
    "h_workers": {"en": "Parallel grading calls", "ko": "동시 채점 수"},
    "h_noopen": {"en": "Don't open the report in a browser", "ko": "리포트를 브라우저로 열지 않음"},
    "h_report": {"en": "Rebuild the report from saved runs", "ko": "저장된 기록으로 리포트만 다시 만듭니다"},
    "h_history": {"en": "Score table per run", "ko": "회차별 점수 표"},
    "h_summary": {"en": "Print the latest run as text: weakest habits, rewrites, missed responses, rules to add",
                  "ko": "최근 회차를 글로 출력: 약한 습관, 고쳐 쓰기, 놓친 응답, 추가할 규칙"},
    "sum_head": {"en": "agent-coach · {date} · overall {overall}/100 · {n} conversations",
                 "ko": "agent-coach · {date} · 종합 {overall}/100 · 대화 {n}개"},
    "sum_weak": {"en": "Weakest habits", "ko": "약한 습관"},
    "sum_rewrites": {"en": "Rewrites of your prompts", "ko": "내 지시 고쳐 쓰기"},
    "sum_gaps": {"en": "Missed responses caused by a gap in your prompt", "ko": "내 지시의 빈틈 때문에 놓친 응답"},
    "sum_rules": {"en": "Rules worth adding", "ko": "추가할 만한 규칙"},
    "sum_wrote": {"en": "wrote", "ko": "쓴 지시"},
    "sum_better": {"en": "better", "ko": "이렇게"},
    "sum_why": {"en": "why", "ko": "이유"},
}


def t(key: str, lang: str, **kw):
    msg = M[key].get(lang) or M[key]["en"]
    return msg.format(**kw) if isinstance(msg, str) and kw else msg
