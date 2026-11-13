"""Build a report from made-up data, for screenshots and for trying the UI without your own history.

    python scripts/demo_report.py [--lang en|ko] [-o demo.html]

Every conversation, prompt and project name below is fictional.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentcoach.report import render  # noqa: E402
from agentcoach.rubric import load_rubric  # noqa: E402

SESSIONS = [
    ("claude", "todo-api", 14, "Add pagination to the /tasks endpoint",
     "add pagination to tasks",
     "Add cursor pagination to GET /tasks in api/routes/tasks.py (limit default 50, max 200). "
     "Don't change the response shape for existing clients. Done when tests/test_tasks.py passes.",
     "No done criteria and no constraint on the response shape."),
    ("codex", "landing-page", 9, "Fix the mobile navbar overlapping the hero",
     "the navbar is broken on mobile",
     "On iPhone width (390px) the navbar in components/Nav.tsx covers the hero heading. "
     "Screenshot attached. Fix it without changing the desktop layout, then check at 390px and 1280px.",
     "Symptom, screen size and screenshot were missing."),
    ("claude", "data-pipeline", 22, "Migrate the nightly job from cron to Airflow",
     "move the nightly job to airflow",
     "Before changing anything, read jobs/nightly.py and propose a plan for moving it to an Airflow DAG. "
     "Stop after the plan; I'll review it before you write code.",
     "A multi-file migration started without a plan or a stop point."),
    ("codex", "cli-tool", 6, "Rename the --out flag to --output", None, None, None),
    ("claude", "blog", 11, "Write release notes for v2.3",
     "write release notes",
     "Write release notes for v2.3 from the commits since v2.2 (git log v2.2..HEAD). "
     "Audience: end users, not developers. Under 200 words, grouped as New / Fixed.",
     "Audience and length were left for the agent to guess."),
    ("claude", "todo-api", 31, "Debug flaky integration tests", None, None, None),
]

MISSES = [
    {"turn": 3, "signal_turn": 4, "signal": "correction", "cause": "prompt_gap", "context_was_enough": False,
     "original": "deploy it", "what_went_wrong": "Deployed to production; you meant the staging environment.",
     "better": "deploy it to staging", "why": "Which environment was only in your head."},
    {"turn": 7, "signal_turn": 8, "signal": "repeat", "cause": "agent_error", "context_was_enough": True,
     "original": "use the same format as before", "what_went_wrong": "The agent switched from CSV to JSON.",
     "better": "", "why": "The format was set two turns earlier; context was enough."},
    {"turn": 5, "signal_turn": 6, "signal": "redo", "cause": "prompt_gap", "context_was_enough": False,
     "original": "clean up the old branches", "what_went_wrong": "Deleted remote branches too.",
     "better": "clean up the old local branches; don't touch the remote", "why": "Local vs remote wasn't said."},
]

THEMES = [{"title": "Target environment left implicit",
           "rule": "Deploys go to staging unless I say production.",
           "where": "CLAUDE.md / AGENTS.md", "refs": [{"session": "s0", "turn": 3}, {"session": "s4", "turn": 2}]},
          {"title": "Destructive git commands without scope",
           "rule": "Never delete or force-push remote branches without asking.",
           "where": "hook", "refs": [{"session": "s5", "turn": 5}, {"session": "s2", "turn": 9}]}]

SESSIONS_KO = [
    ("claude", "todo-api", 14, "/tasks 엔드포인트에 페이지네이션 추가",
     "할 일 목록 페이지네이션 넣어줘",
     "api/routes/tasks.py 의 GET /tasks 에 커서 페이지네이션 넣어줘 (기본 50개, 최대 200개). "
     "기존 클라이언트 응답 형태는 바꾸지 말고, tests/test_tasks.py 통과하면 끝이야.",
     "완료 기준과 응답 형태 제약이 없었습니다."),
    ("codex", "landing-page", 9, "모바일에서 상단 메뉴가 히어로를 가리는 문제",
     "모바일에서 메뉴 깨져",
     "아이폰 폭(390px)에서 components/Nav.tsx 메뉴가 히어로 제목을 가려. 스크린샷 첨부할게. "
     "데스크톱 레이아웃은 그대로 두고 고친 뒤 390px, 1280px 둘 다 확인해줘.",
     "증상, 화면 크기, 스크린샷이 빠졌습니다."),
    ("claude", "data-pipeline", 22, "야간 배치를 cron 에서 Airflow 로 옮기기",
     "야간 작업 airflow로 옮겨줘",
     "바꾸기 전에 jobs/nightly.py 읽고 Airflow DAG 로 옮기는 계획부터 보여줘. "
     "계획까지만 하고 멈춰. 내가 보고 나서 코드 작성해.",
     "여러 파일을 바꾸는 이전 작업을 계획과 멈출 지점 없이 시작했습니다."),
    ("codex", "cli-tool", 6, "--out 옵션 이름을 --output 으로 변경", None, None, None),
    ("claude", "blog", 11, "v2.3 릴리스 노트 작성",
     "릴리스 노트 써줘",
     "v2.2 이후 커밋(git log v2.2..HEAD)으로 v2.3 릴리스 노트 써줘. "
     "개발자 말고 일반 사용자 대상, 200단어 이내, 새 기능 / 수정으로 나눠서.",
     "독자와 분량을 에이전트가 추측해야 했습니다."),
    ("claude", "todo-api", 31, "가끔 실패하는 통합 테스트 디버깅", None, None, None),
]

MISSES_KO = [
    {"turn": 3, "signal_turn": 4, "signal": "correction", "cause": "prompt_gap", "context_was_enough": False,
     "original": "배포해", "what_went_wrong": "운영 서버에 배포했는데, 원한 건 스테이징이었습니다.",
     "better": "스테이징에 배포해", "why": "어느 환경인지는 나만 알고 있었습니다."},
    {"turn": 7, "signal_turn": 8, "signal": "repeat", "cause": "agent_error", "context_was_enough": True,
     "original": "아까랑 같은 형식으로", "what_went_wrong": "에이전트가 CSV 에서 JSON 으로 바꿨습니다.",
     "better": "", "why": "형식은 두 턴 전에 정해졌으니 맥락은 충분했습니다."},
    {"turn": 5, "signal_turn": 6, "signal": "redo", "cause": "prompt_gap", "context_was_enough": False,
     "original": "오래된 브랜치 정리해", "what_went_wrong": "원격 브랜치까지 지웠습니다.",
     "better": "오래된 로컬 브랜치만 정리해. 원격은 건드리지 마", "why": "로컬인지 원격인지 말하지 않았습니다."},
]

THEMES_KO = [{"title": "배포 대상 환경을 말하지 않음",
              "rule": "따로 말하지 않으면 배포는 스테이징으로 한다.",
              "where": "CLAUDE.md / AGENTS.md", "refs": THEMES[0]["refs"]},
             {"title": "범위 없는 위험한 git 명령",
              "rule": "원격 브랜치 삭제·강제 푸시는 묻기 전에 하지 않는다.",
              "where": "훅", "refs": THEMES[1]["refs"]}]

NOTES = {"en": ("stated clearly.", "partly stated.", "missing.", "not needed here."),
         "ko": ("분명히 말했습니다.", "일부만 말했습니다.", "빠졌습니다.", "필요 없는 대화였습니다.")}


def make_run(rubric, created, base, seed):
    ko = rubric.get("lang") == "ko"
    sessions_src, misses_src, themes = (SESSIONS_KO, MISSES_KO, THEMES_KO) if ko else (SESSIONS, MISSES, THEMES)
    good, part, miss, na = NOTES["ko" if ko else "en"]
    rnd = random.Random(seed)
    dims = {}
    for i, d in enumerate(rubric["dimensions"]):
        dims[d["id"]] = {"score": max(5, min(98, base[i])), "n": 6, "missed": rnd.randint(0, 3)}
    sessions = []
    for k, (src, proj, turns, summary, orig, better, why) in enumerate(sessions_src):
        sd = {}
        for d in rubric["dimensions"]:
            v = rnd.choice([0, 1, 1, 2, 2, None])
            sd[d["id"]] = {"score": v, "evidence_turn": 1, "note": f"{d['short']}: " +
                           (good if v == 2 else part if v == 1 else miss if v == 0 else na), "excerpt": orig or summary}
        coaching = [{"dimension": rubric["dimensions"][k % 4 + 1]["id"], "turn": 1,
                     "original": orig, "better": better, "why": why}] if orig else []
        misses = [misses_src[{0: 0, 2: 2, 5: 1}[k]]] if k in (0, 2, 5) else []
        sessions.append({"id": f"s{k}", "source": src, "project": proj, "started": created, "ended": created,
                         "turns": turns, "task_summary": summary, "judge": "claude:sonnet",
                         "models": [{"model": "claude-opus-5-5" if src == "claude" else "gpt-5.6-sol",
                                     "effort": ["medium", "high", "low"][k % 3], "turns": turns}],
                         "dimensions": sd, "coaching": coaching, "misses": misses})
    scored = [v["score"] for v in dims.values()]
    return {"schema": 1, "created": created, "judge": "claude:sonnet", "sources": ["claude", "codex"],
            "rubric": {"id": rubric.get("id"), "version": rubric["version"]}, "session_count": len(sessions),
            "overall": round(sum(scored) / len(scored)), "dimensions": dims, "sessions": sessions,
            "misses": {"total": 3, "by_cause": {"prompt_gap": 2, "agent_error": 1}, "turns": 93,
                       "gap_share": 67, "gaps_per_100_turns": 2.2, "themes": themes}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en")
    ap.add_argument("-o", "--out", default="demo-report.html")
    a = ap.parse_args()
    rubric = load_rubric(lang=a.lang)
    runs = [make_run(rubric, "2026-10-30T09:00:00+00:00", [48, 22, 41, 70, 45, 30, 35, 50, 72, 60, 38, 55], 1),
            make_run(rubric, "2026-11-13T09:00:00+00:00", [64, 41, 55, 83, 58, 49, 47, 63, 80, 78, 52, 70], 2)]
    Path(a.out).write_text(render(runs, rubric), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
