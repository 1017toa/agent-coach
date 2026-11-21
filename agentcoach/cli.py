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
from .i18n import SUPPORTED, detect_lang, t
from .judge import judge_many, summarize_gaps
from .paths import coach_home
from .report import render
from .rubric import load_rubric
from .store import build_run, load_runs, save_run


def _since(args, runs) -> datetime | None:
    if args.all:
        return None
    if args.days:
        return datetime.now(timezone.utc) - timedelta(days=args.days)
    if runs:
        # default: only conversations since the previous run, so each run measures new habits
        last = runs[-1]
        return datetime.fromisoformat(last.get("window_end") or last["created"])
    return datetime.now(timezone.utc) - timedelta(days=14)


def _sources(arg: str, lang: str) -> list[str]:
    s = [x.strip() for x in arg.split(",") if x.strip()]
    bad = set(s) - {"claude", "codex"}
    if bad:
        sys.exit(t("bad_source", lang, bad=", ".join(sorted(bad))))
    return s


def _pick_judge(choice: str) -> str:
    if choice != "auto":
        return choice
    if shutil.which("claude"):
        return "claude"
    if shutil.which("codex"):
        return "codex"
    return "heuristic"


def _lang(args, runs=None) -> str:
    """--lang, else the language the latest run was graded in, else the OS locale."""
    if getattr(args, "lang", None):
        return args.lang
    if runs and runs[-1].get("lang") in SUPPORTED:
        return runs[-1]["lang"]
    return detect_lang()


def _write_report(runs, rubric_path, lang, no_open):
    out = coach_home() / "report.html"
    out.write_text(render(runs, load_rubric(rubric_path, lang)), encoding="utf-8")
    if not no_open:
        webbrowser.open(out.as_uri())
    return out


def cmd_scan(args) -> None:
    runs = load_runs()
    lang = _lang(args, runs)
    since = _since(args, runs)
    sessions = collect(_sources(args.source, lang), since, args.include_sdk)
    when = since.astimezone().strftime("%Y-%m-%d %H:%M") if since else t("all_time", lang)
    print(t("scan_head", lang, since=when, n=len(sessions)))
    for (src, proj), n in Counter((s.source, s.project) for s in sessions).most_common(30):
        print(f"  {src:6} {n:4}  {proj}")
    if sessions:
        print(t("scan_tail", lang, turns=sum(len(s.turns) for s in sessions), max=args.max_sessions))


def cmd_run(args) -> None:
    runs = load_runs()
    lang = _lang(args, runs)
    rubric = load_rubric(args.rubric, lang)
    since = _since(args, runs)
    sessions = collect(_sources(args.source, lang), since, args.include_sdk)
    if not sessions:
        sys.exit(t("nothing", lang))
    sample = pick_sample(sessions, args.max_sessions)
    judge = _pick_judge(args.judge)
    print(t("grading", lang, k=len(sample), n=len(sessions), judge=judge))

    results = {s.id: score_session(s, rubric) for s in sample}
    if judge in ("claude", "codex"):
        done = [0]

        def tick(s, r):
            done[0] += 1
            mark = t("fallback", lang) if "error" in r else t("done", lang)
            print(f"  [{done[0]}/{len(sample)}] {s.project[:40]} … {mark}", flush=True)
            if "error" in r and args.verbose:
                print("     ", r["error"][:300])

        judged = judge_many(sample, rubric, judge, args.model, lang, args.workers, tick)
        ok = 0
        for sid, r in judged.items():
            if "error" not in r:
                results[sid] = r
                ok += 1
        if ok == 0:
            print(t("all_failed", lang))
            judge = "heuristic"
    label = judge if judge == "heuristic" else f"{judge}:{args.model or 'default'}"
    run = build_run(sample, results, rubric, since.isoformat() if since else None, label)
    run["lang"] = lang
    run["window_end"] = datetime.now(timezone.utc).isoformat()
    gaps = [{**m, "project": sess["project"], "session": sess["id"]}
            for sess in run["sessions"] for m in sess.get("misses", []) if m["cause"] == "prompt_gap"]
    if judge in ("claude", "codex") and len(gaps) >= 2:
        print(t("grouping", lang), flush=True)
        themes = summarize_gaps(gaps, judge, args.model, lang)
        for th in themes:
            th["refs"] = [{"session": gaps[i]["session"], "turn": gaps[i]["turn"]} for i in th.pop("items")]
        run["misses"]["themes"] = themes
    path = save_run(run)
    out = _write_report(load_runs(), args.rubric, lang, args.no_open)
    ms = run["misses"]
    print("\n" + t("result", lang, overall=run["overall"], total=ms["total"],
                   gaps=ms["by_cause"].get("prompt_gap", 0), path=path, out=out))


def cmd_report(args) -> None:
    runs = load_runs()
    lang = _lang(args, runs)
    if not runs:
        sys.exit(t("no_runs", lang))
    print(_write_report(runs, args.rubric, lang, args.no_open))


def cmd_summary(args) -> None:
    """Plain-text digest of the latest run, for reading in a terminal or by an agent skill."""
    runs = load_runs()
    lang = _lang(args, runs)
    if not runs:
        sys.exit(t("no_runs", lang))
    run, rubric = runs[-1], load_rubric(args.rubric, lang)
    names = {d["id"]: d for d in rubric["dimensions"]}
    k = args.limit
    print(t("sum_head", lang, date=run["created"][:10], overall=run["overall"], n=run["session_count"]))
    scored = [(v["score"], i) for i, v in run["dimensions"].items() if v.get("score") is not None and i in names]
    print()
    print("## " + t("sum_weak", lang))
    for sc, i in sorted(scored)[:3]:
        print(f"- {names[i]['name']} {sc}: {names[i]['summary']}")
    rewrites = [(s, c) for s in run["sessions"] for c in s.get("coaching", []) if c.get("better")]
    if rewrites:
        print()
        print("## " + t("sum_rewrites", lang))
        for s, c in rewrites[:k]:
            dim = names.get(c.get("dimension"), {}).get("name", "")
            print(f"- [{dim}] {s['project']} turn {c.get('turn')}")
            print(f"  {t('sum_wrote', lang)}: {c['original']}")
            print(f"  {t('sum_better', lang)}: {c['better']}")
            print(f"  {t('sum_why', lang)}: {c.get('why', '')}")
    gaps = [(s, m) for s in run["sessions"] for m in s.get("misses", []) if m.get("cause") == "prompt_gap"]
    if gaps:
        print()
        print("## " + t("sum_gaps", lang))
        for s, m in gaps[:k]:
            print(f"- {s['project']} turn {m.get('turn')}: {m.get('original', '')}")
            print(f"  {m.get('what_went_wrong', '')}")
            if m.get("better"):
                print(f"  {t('sum_better', lang)}: {m['better']}")
    themes = (run.get("misses") or {}).get("themes") or []
    if themes:
        print()
        print("## " + t("sum_rules", lang))
        for th in themes:
            print(f"- {th['rule']}  ({th['where']}; {th['title']})")


def cmd_rank(args) -> None:
    import json as _json
    from .card import render_card
    from .rank import MIN_CONVERSATIONS, issue_url, payload, weekly
    runs = load_runs()
    lang = _lang(args, runs)
    rubric = load_rubric(args.rubric, lang)
    w = weekly(runs, rubric, days=args.days)
    print(t("rank_head", lang, week=w["week"], days=w["days"], n=w["conversations"]))
    if not w["conversations"]:
        sys.exit(t("rank_none", lang))
    print(t("rank_score", lang, score=w["score"], quality=w["quality"], bonus=w["bonus"]))
    from .rank import tier_of
    tr = tier_of(w["score"])
    nxt = t("rank_next", lang, gap=tr["gap"], tier=tr["next_ko" if lang == "ko" else "next_en"]) \
        if tr["next"] else t("rank_top", lang)
    print(t("rank_tier", lang, tier=tr["ko" if lang == "ko" else "en"], next=nxt))
    if w["improvement"] is not None:
        print(t("rank_imp", lang, imp=("+" if w["improvement"] >= 0 else "") + str(w["improvement"])))
    if not w["eligible"]:
        print(t("rank_min", lang, min=MIN_CONVERSATIONS))
    rdir = coach_home() / "rank"
    rdir.mkdir(exist_ok=True)
    prof = rdir / "profile.json"
    saved = _json.loads(prof.read_text(encoding="utf-8")) if prof.exists() else {}
    nick = args.nickname or saved.get("nickname") or ""
    league = args.league if args.league is not None else saved.get("league", "")
    if args.nickname or args.league is not None:
        prof.write_text(_json.dumps({"nickname": nick, "league": league}, ensure_ascii=False), encoding="utf-8")
    p = payload(w, nick or "anonymous", league)
    (rdir / f"{w['week']}.json").write_text(_json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    card = rdir / f"card-{w['week']}.html"
    card.write_text(render_card(p, rubric, lang, MIN_CONVERSATIONS), encoding="utf-8")
    print(t("rank_card", lang, path=card))
    if not args.no_open:
        webbrowser.open(card.as_uri())
    if args.submit:
        if not nick:
            sys.exit(t("rank_nick", lang))
        if not w["eligible"]:
            sys.exit(t("rank_min", lang, min=MIN_CONVERSATIONS))
        print(t("rank_sub", lang))
        print(_json.dumps(p, ensure_ascii=False))
        webbrowser.open(issue_url(args.repo, p))


def cmd_history(args) -> None:
    runs = load_runs()
    lang = _lang(args, runs)
    if not runs:
        print(t("no_history", lang))
        return
    rubric = load_rubric(args.rubric, lang)
    date_h, overall_h, convo_h, judge_h = t("hist_head", lang)
    heads = [d["short"] for d in rubric["dimensions"]]
    print(f"{date_h:<10}  {overall_h:>7}  " + "  ".join(f"{h:>8}" for h in heads) + f"  {convo_h:>6}  {judge_h}")
    for r in runs:
        vals = [r["dimensions"].get(d["id"], {}).get("score") for d in rubric["dimensions"]]
        print(f"{r['created'][:10]}  {str(r['overall'] if r['overall'] is not None else '-'):>7}  "
              + "  ".join(f"{'-' if v is None else v:>8}" for v in vals)
              + f"  {r['session_count']:>6}  {r['judge']}")


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # help text follows --lang if given on the command line, else the OS locale
    argv = sys.argv[1:] if argv is None else argv
    hl = next((argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--lang"), None) or detect_lang()
    hl = hl if hl in SUPPORTED else "en"
    h = lambda k: t(k, hl)  # noqa: E731

    p = argparse.ArgumentParser(prog="agent-coach", description=h("desc"))
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, window=True):
        sp.add_argument("--rubric", help=h("h_rubric"))
        sp.add_argument("--lang", choices=list(SUPPORTED), help=h("h_lang"))
        if window:
            sp.add_argument("--source", default="claude,codex", help=h("h_source"))
            sp.add_argument("--days", type=int, help=h("h_days"))
            sp.add_argument("--all", action="store_true", help=h("h_all"))
            sp.add_argument("--include-sdk", action="store_true", help=h("h_sdk"))
            sp.add_argument("--max-sessions", type=int, default=20, help=h("h_max"))

    sp = sub.add_parser("scan", help=h("h_scan"))
    common(sp)
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("run", help=h("h_run"))
    common(sp)
    sp.add_argument("--judge", default="auto", choices=["auto", "claude", "codex", "heuristic"], help=h("h_judge"))
    sp.add_argument("--model", help=h("h_model"))
    sp.add_argument("--workers", type=int, default=3, help=h("h_workers"))
    sp.add_argument("--no-open", action="store_true", help=h("h_noopen"))
    sp.add_argument("--verbose", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("report", help=h("h_report"))
    common(sp, window=False)
    sp.add_argument("--no-open", action="store_true", help=h("h_noopen"))
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("summary", help=h("h_summary"))
    common(sp, window=False)
    sp.add_argument("--limit", type=int, default=5)
    sp.set_defaults(func=cmd_summary)

    sp = sub.add_parser("rank", help=h("h_rank"))
    common(sp, window=False)
    sp.add_argument("--days", type=int, default=7, help=h("h_days"))
    sp.add_argument("--nickname", help=h("h_nick"))
    sp.add_argument("--league", help=h("h_league"))
    sp.add_argument("--submit", action="store_true", help=h("h_submit"))
    sp.add_argument("--repo", default="1017toa/agent-coach", help=argparse.SUPPRESS)
    sp.add_argument("--no-open", action="store_true", help=h("h_noopen"))
    sp.set_defaults(func=cmd_rank)

    sp = sub.add_parser("history", help=h("h_history"))
    common(sp, window=False)
    sp.set_defaults(func=cmd_history)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
