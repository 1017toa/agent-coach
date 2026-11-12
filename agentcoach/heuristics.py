"""Offline scorer: keyword/shape signals only, no model calls.

It is deliberately rough. It exists so a first report works with zero setup
(and in a classroom without spending anyone's quota); the LLM judge is the
real coach. Each rule returns 0/1/2 or None (not applicable).
"""
from __future__ import annotations

import re

from .collect import Session

R = lambda p: re.compile(p, re.I)  # noqa: E731

PATH = R(r"(@[\w./\\-]+|[\w\-]+[/\\][\w./\\-]+|\b[\w\-]+\.(py|ts|tsx|js|jsx|go|rs|java|kt|cs|cpp|c|h|rb|php|md|json|ya?ml|toml|html|css|sql|sh|ps1)\b|:\d+\b)")
SYMPTOM = R(r"(에러|오류|실패|안 ?돼|안 ?됨|깨져|버그|증상|재현|error|fail|exception|traceback|crash|bug|doesn'?t work|broken)")
VERIFY = R(r"(테스트|test|pytest|jest|통과|pass|빌드|build|lint|린트|타입체크|typecheck|검증|확인해|재현|돌려 ?봐|실행해 ?봐|스크린샷|screenshot|until .* pass|될 때까지)")
CONSTRAINT = R(r"(하지 ?마|말고|없이|금지|건드리지|유지|그대로 두|만 ?(수정|고쳐)|패턴(을|대로)? 따라|don'?t|do not|without|no new|keep|only|avoid|must not|instead of)")
SCOPE = R(r"(최소(한)?|간단히|간단하게|빠르게 대충|넉넉|꼼꼼|빠짐없이|엣지 ?케이스|edge case|빈 ?상태|에러 ?상태|be ambitious|minimal|just the|fully|end[- ]to[- ]end|전부|모두 다)")
PLAN = R(r"(계획|플랜|plan|설계|먼저 .*(말해|알려|정리)|질문(해|하고)|인터뷰|interview|spec|스펙|단계별|마일스톤|milestone)")
EVIDENCE = R(r"(보여줘|보여 ?달|출력(을|도)? ?(보여|붙여)|로그(를|도)? ?(보여|붙여)|증거|스크린샷|캡처|evidence|show me|paste the output|결과(를)? (보여|붙여))")
CORRECTION = R(r"^(아니|아냐|그게 아니|다시|또|여전히|still|no[,. ]|wrong|not what|그대로잖|안 ?바뀌|똑같)")
ERRDUMP = R(r"(Traceback|Error:|Exception|at .+:\d+|\bline \d+|```)")
STOPS = R(r"(멈춰|멈추고|물어보고|물어봐|확인받|승인(하면|받|한 ?뒤)|제출 ?전|하기 ?전에|직전에|묻지 ?말고|알아서 (진행|끝까지)|ask me|stop and|before (you )?(submit|delete|push|send)|keep going|don'?t ask)")
DURABLE = R(r"(앞으로|항상|매번|무조건|절대|from now on|always|every time|never)")
RECORD = R(r"(CLAUDE\.md|AGENTS\.md|메모리|기억해|규칙(으로|에)|스킬|skill|훅|hook|memory)")


def _task_prompts(s: Session) -> list:
    """Turns that start or substantially reframe work (long enough to carry a spec)."""
    out = [t for t in s.turns if not t.slash and (t.index == 1 or len(t.text) >= 60)]
    return out or [t for t in s.turns if not t.slash][:1]


def score_session(s: Session, rubric: dict) -> dict:
    tasks = _task_prompts(s)
    typed = [t for t in s.turns if not t.slash]
    all_text = "\n".join(t.text for t in typed)
    task_text = "\n".join(t.text for t in tasks)
    big = len(typed) >= 6 or len(task_text) >= 400
    first = tasks[0] if tasks else None

    def first_turn(rx):
        for t in typed:
            if rx.search(t.text):
                return t.index
        return None

    def graded(rx, text_first, text_any):
        if rx.search(text_first):
            return 2
        if rx.search(text_any):
            return 1
        return 0

    dims = {}
    ft = first.text if first else ""
    actionable = bool(re.search(r"(해줘|해 ?주세요|만들어|고쳐|수정|추가|바꿔|구현|fix|add|make|build|implement|change|refactor|write)", all_text, re.I))

    ctx = 2 if (PATH.search(ft) and (SYMPTOM.search(ft) or len(ft) > 120)) else (1 if PATH.search(task_text) or SYMPTOM.search(ft) or len(ft) > 200 else 0)
    dims["specific_context"] = ctx if actionable else None
    dims["done_criteria"] = graded(VERIFY, ft, all_text) if actionable else None
    dims["constraints"] = graded(CONSTRAINT, ft, task_text) if actionable else None
    has_material = any(t.images for t in typed) or "@" in all_text or ERRDUMP.search(all_text)
    mentions_err = SYMPTOM.search(all_text)
    dims["hand_over"] = (2 if has_material else 0) if (mentions_err or any(t.images for t in typed)) else None
    dims["scope_signal"] = (graded(SCOPE, ft, task_text)) if actionable and big else None
    planned = any(t.slash in ("/plan", "/goal") for t in s.turns) or PLAN.search(ft)
    dims["plan_first"] = (2 if planned else (1 if PLAN.search(all_text) else 0)) if big else None
    claimed_done = any(re.search(r"(완료|끝났|done|fixed|passed|통과)", t.agent_after, re.I) for t in s.turns)
    dims["evidence"] = (2 if EVIDENCE.search(all_text) else 0) if claimed_done and actionable else None

    # longest run of consecutive correction-style prompts without a reset
    run = best = 0
    for t in s.turns:
        if t.slash in ("/clear", "/rewind", "/compact", "/new"):
            run = 0
        elif CORRECTION.search(t.text.strip()):
            run += 1
            best = max(best, run)
        else:
            run = 0
    corrections = sum(1 for t in typed if CORRECTION.search(t.text.strip()))
    dims["steering"] = None if corrections == 0 else (2 if best <= 1 else 1 if best == 2 else 0)

    risky = re.search(r"(제출|지원|결제|구매|삭제|지워|전송|보내|게시|업로드|푸시|push|submit|delete|send|publish|pay)", all_text, re.I)
    dims["stop_conditions"] = graded(STOPS, ft, task_text) if actionable and (big or risky) else None

    durable_turns = [t for t in typed if DURABLE.search(t.text)]
    if not durable_turns:
        dims["reusable_guidance"] = None
    elif any(RECORD.search(t.text) for t in typed):
        dims["reusable_guidance"] = 2
    else:
        dims["reusable_guidance"] = 0 if len(durable_turns) >= 3 else 1

    resets = sum(1 for t in s.turns if t.slash in ("/clear", "/compact", "/new", "/fork"))
    if len(typed) < 15:
        dims["focused_session"] = None
    elif len(typed) >= 60 and resets == 0:
        dims["focused_session"] = 0
    else:
        dims["focused_session"] = 1 if (len(typed) >= 30 and resets == 0) else 2

    rx_for = {"specific_context": PATH, "done_criteria": VERIFY, "constraints": CONSTRAINT,
              "scope_signal": SCOPE, "plan_first": PLAN, "evidence": EVIDENCE, "steering": CORRECTION,
              "hand_over": ERRDUMP, "stop_conditions": STOPS, "reusable_guidance": DURABLE}
    out = {}
    for d in rubric["dimensions"]:
        did = d["id"]
        sc = dims.get(did)
        out[did] = {"score": sc, "evidence_turn": first_turn(rx_for[did]) if did in rx_for else None,
                    "note": ""}
    return {"task_summary": (ft[:80] + "…") if len(ft) > 80 else ft, "dimensions": out, "coaching": [],
            "judge": "heuristic"}
