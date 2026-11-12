from __future__ import annotations

import argparse
import shutil
import sys
import webbrowser
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import __version__
from .collect import collect, pick_sample
from .heuristics import score_session
from .judge import judge_many
from .paths import coach_home
from .report import render
from .rubric import load_rubric
from .store import build_run, load_runs, save_run


def _since(args, runs) -> datetime | None:
    if args.all:
        return None
    if args.days:
        return datetime.now(timezone.utc) - timedelta(days=args.days)
    if runs and not args.days:
        # default: only conversations since the previous run, so each run measures new habits
        return datetime.fromisoformat(runs[-1]["window_end"]) if runs[-1].get("window_end") else \
            datetime.fromisoformat(runs[-1]["created"])
    return datetime.now(timezone.utc) - timedelta(days=14)


def _sources(arg: str) -> list[str]:
    s = [x.strip() for x in arg.split(",") if x.strip()]
    bad = set(s) - {"claude", "codex"}
    if bad:
        sys.exit(f"알 수 없는 source: {', '.join(bad)} (claude, codex 중에서)")
    return s


def _pick_judge(choice: str) -> str:
    if choice != "auto":
        return choice
    if shutil.which("claude"):
        return "claude"
    if shutil.which("codex"):
        return "codex"
    return "heuristic"


def cmd_scan(args) -> None:
    runs = load_runs()
    since = _since(args, runs)
    sessions = collect(_sources(args.source), since, args.include_sdk)
    print(f"기간: {since.astimezone().strftime('%Y-%m-%d %H:%M') if since else '전체'} 이후  ·  대화 {len(sessions)}개")
    by = Counter((s.source, s.project) for s in sessions)
    for (src, proj), n in by.most_common(30):
        print(f"  {src:6} {n:4}  {proj}")
    if sessions:
        turns = sum(len(s.turns) for s in sessions)
        print(f"사람이 쓴 지시 {turns}개. `agent-coach run` 으로 채점합니다 (기본 최대 {args.max_sessions}개 대화).")


def cmd_run(args) -> None:
    rubric = load_rubric(args.rubric)
    runs = load_runs()
    since = _since(args, runs)
    sessions = collect(_sources(args.source), since, args.include_sdk)
    if not sessions:
        sys.exit("채점할 대화가 없습니다. --days 30 이나 --all 로 기간을 넓혀 보세요.")
    sample = pick_sample(sessions, args.max_sessions)
    judge = _pick_judge(args.judge)
    print(f"대화 {len(sessions)}개 중 {len(sample)}개를 채점합니다 · 채점기: {judge}")

    results = {s.id: score_session(s, rubric) for s in sample}
    if judge in ("claude", "codex"):
        done = [0]

        def tick(s, r):
            done[0] += 1
            mark = "실패, 키워드 채점으로 대체" if "error" in r else "완료"
            print(f"  [{done[0]}/{len(sample)}] {s.project[:40]} … {mark}", flush=True)
            if "error" in r and args.verbose:
                print("     ", r["error"][:300])

        judged = judge_many(sample, rubric, judge, args.model, args.lang, args.workers, tick)
        ok = 0
        for sid, r in judged.items():
            if "error" not in r:
                results[sid] = r
                ok += 1
        if ok == 0:
            print("LLM 채점이 모두 실패해 키워드 채점 결과만 저장합니다. --verbose 로 원인을 확인하세요.")
            judge = "heuristic"
    label = judge if judge == "heuristic" else f"{judge}:{args.model or 'default'}"
    run = build_run(sample, results, rubric, since.isoformat() if since else None, label)
    run["window_end"] = datetime.now(timezone.utc).isoformat()
    path = save_run(run)
    runs = load_runs()
    out = coach_home() / "report.html"
    out.write_text(render(runs, rubric), encoding="utf-8")
    print(f"\n종합 {run['overall']}점 · 기록 {path}\n리포트 {out}")
    if not args.no_open:
        webbrowser.open(out.as_uri())


def cmd_report(args) -> None:
    runs = load_runs()
    if not runs:
        sys.exit("아직 채점 기록이 없습니다. 먼저 `agent-coach run` 을 실행하세요.")
    out = coach_home() / "report.html"
    out.write_text(render(runs, load_rubric(args.rubric)), encoding="utf-8")
    print(out)
    if not args.no_open:
        webbrowser.open(out.as_uri())


def cmd_history(args) -> None:
    runs = load_runs()
    if not runs:
        print("기록 없음")
        return
    rubric = load_rubric(args.rubric)
    heads = [d["short"] for d in rubric["dimensions"]]
    print("날짜        종합  " + "  ".join(f"{h:>3}" for h in heads) + "  대화  채점기")
    for r in runs:
        vals = [r["dimensions"].get(d["id"], {}).get("score") for d in rubric["dimensions"]]
        print(f"{r['created'][:10]}  {str(r['overall'] or '-'):>4}  "
              + "  ".join(f"{'-' if v is None else v:>3}" for v in vals)
              + f"  {r['session_count']:>4}  {r['judge']}")


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="agent-coach",
                                description="Claude Code·Codex 대화 기록으로 공식 가이드 기준 지시 습관을 코칭합니다.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, window=True):
        sp.add_argument("--rubric", help="채점표 JSON 경로 (기본: 공식 가이드 기반)")
        if window:
            sp.add_argument("--source", default="claude,codex", help="claude,codex 중 선택 (기본 둘 다)")
            sp.add_argument("--days", type=int, help="최근 N일 (기본: 지난 채점 이후, 첫 회는 14일)")
            sp.add_argument("--all", action="store_true", help="기간 제한 없이 전체")
            sp.add_argument("--include-sdk", action="store_true", help="스크립트로 돌린 claude -p / codex exec 대화도 포함")
            sp.add_argument("--max-sessions", type=int, default=20, help="채점할 최대 대화 수 (기본 20)")

    sp = sub.add_parser("scan", help="채점 대상 대화를 미리 봅니다 (모델 호출 없음)")
    common(sp)
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("run", help="채점하고 기록을 남긴 뒤 리포트를 엽니다")
    common(sp)
    sp.add_argument("--judge", default="auto", choices=["auto", "claude", "codex", "heuristic"],
                    help="채점기 (기본 auto: claude → codex → 키워드)")
    sp.add_argument("--model", help="채점에 쓸 모델 (예: sonnet, haiku, gpt-5.5)")
    sp.add_argument("--workers", type=int, default=3, help="동시 채점 수")
    sp.add_argument("--lang", default="ko", choices=["ko", "en"])
    sp.add_argument("--no-open", action="store_true", help="리포트를 브라우저로 열지 않음")
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("report", help="저장된 기록으로 리포트만 다시 만듭니다")
    common(sp, window=False)
    sp.add_argument("--no-open", action="store_true")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("history", help="회차별 점수 표")
    common(sp, window=False)
    sp.set_defaults(func=cmd_history)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
