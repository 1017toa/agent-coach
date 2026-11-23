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
    "h_rank": {"en": "Weekly score for the ranking, a share card, and an optional submission",
               "ko": "랭킹용 주간 점수와 공유 카드 만들기, 원하면 제출"},
    "h_nick": {"en": "Name shown on the card and leaderboard (saved for next time)",
               "ko": "카드와 랭킹에 보일 이름 (다음에도 사용)"},
    "h_league": {"en": "League tag, e.g. a class or team, to compare within a group",
                 "ko": "리그 태그 (반·팀 등). 같은 리그끼리 따로 순위"},
    "h_submit": {"en": "Open a pre-filled GitHub issue to submit to the public leaderboard",
                 "ko": "공개 랭킹에 제출할 GitHub 이슈를 미리 채워 열기"},
    "rank_head": {"en": "Week {week} (last {days} days) · {n} LLM-graded conversations",
                  "ko": "{week} 주 (최근 {days}일) · LLM으로 채점한 대화 {n}개"},
    "rank_score": {"en": "Weekly score {score} = quality {quality} x activity bonus {bonus}",
                   "ko": "주간 점수 {score} = 품질 {quality} × 활동 보너스 {bonus}"},
    "rank_imp": {"en": "Change vs the week before: {imp}", "ko": "지난주 대비: {imp}"},
    "rank_none": {"en": "No LLM-graded conversations in this window. Run `agent-coach run` first (offline keyword scores don't count).",
                  "ko": "이 기간에 LLM으로 채점한 대화가 없습니다. 먼저 `agent-coach run`을 돌려 주세요 (키워드 채점은 제외)."},
    "rank_min": {"en": "Not ranked yet: at least {min} graded conversations are needed.",
                 "ko": "아직 순위 대상이 아닙니다: 채점한 대화가 {min}개 이상 필요합니다."},
    "rank_card": {"en": "Share card {path}", "ko": "공유 카드 {path}"},
    "rank_nick": {"en": "Choose a nickname first: agent-coach rank --nickname <name> --submit",
                  "ko": "먼저 닉네임을 정해 주세요: agent-coach rank --nickname <이름> --submit"},
    "rank_sub": {"en": "Opening a pre-filled GitHub issue. Check it and press Submit; only the numbers below are sent:",
                 "ko": "미리 채운 GitHub 이슈를 엽니다. 확인 후 Submit을 누르면 아래 숫자만 올라갑니다:"},
    "rank_tier": {"en": "Tier: {tier} ({next})", "ko": "티어: {tier} ({next})"},
    "rank_next": {"en": "{gap} points to {tier}", "ko": "{tier}까지 {gap}점"},
    "rank_top": {"en": "top tier", "ko": "최고 티어"},
    "h_setup": {"en": "Check the setup the agent runs in: deny rules, sandbox, hooks, CI, CLAUDE.md / AGENTS.md (local files only)",
                "ko": "에이전트가 돌아가는 환경 점검: deny 규칙·샌드박스·훅·CI·CLAUDE.md/AGENTS.md (로컬 파일만 읽음)"},
    "h_project": {"en": "Project folder to check (default: current folder)", "ko": "점검할 프로젝트 폴더 (기본: 현재 폴더)"},
    "h_json": {"en": "Print JSON instead of text", "ko": "글 대신 JSON 으로 출력"},
    "setup_head": {"en": "Setup check · {project} · {score}/100", "ko": "환경 점검 · {project} · {score}/100"},
    "setup_areas": {"en": {"safety": "Safety", "verification": "Verification", "instructions": "Instructions"},
                    "ko": {"safety": "안전", "verification": "검증", "instructions": "지시 파일"}},
    "setup_files": {"en": "Read {n} file(s); nothing was sent anywhere.", "ko": "파일 {n}개를 읽었고, 어디로도 보내지 않았습니다."},
    "setup_fix": {"en": "fix", "ko": "고치기"},
    "setup_why": {"en": "As the agent steers and approves on its own, guarantees live in the harness and environment. Source: {src}",
                  "ko": "에이전트가 알아서 판단하고 승인할수록, 보장은 하네스와 환경이 맡아야 합니다. 근거: {src}"},
}


def t(key: str, lang: str, **kw):
    msg = M[key].get(lang) or M[key]["en"]
    return msg.format(**kw) if isinstance(msg, str) and kw else msg
