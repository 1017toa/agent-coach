# Contributing to agent-coach

Thanks for helping. agent-coach is a small, dependency-free Python package, so getting started is quick.

## Setup

```bash
git clone https://github.com/1017toa/agent-coach.git
cd agent-coach
python -m unittest discover -s tests      # run the tests
python scripts/demo_report.py             # build a report from made-up data → demo-report.html
python -m agentcoach scan                 # see what would be graded from your own history
```

No install is needed; `python -m agentcoach` runs from the checkout.

## Where things live

| Path | What it does |
|---|---|
| `agentcoach/collect.py` | Parses Claude Code and Codex transcripts, filters out automated turns |
| `agentcoach/redact.py` | Masks secrets and contact details before anything is sent to a judge |
| `agentcoach/judge.py` | Builds the judge prompt and JSON schema, calls the `claude` / `codex` CLI |
| `agentcoach/heuristics.py` | Offline keyword scoring |
| `agentcoach/rubric/default.json` | The 12 habits, examples and guide citations (Korean base, `*_en` fields for English) |
| `agentcoach/report.py` | Self-contained HTML report; UI strings in the `UI` table |
| `agentcoach/i18n.py` | CLI messages in English and Korean |
| `skills/coach/SKILL.md` | The skill the Claude Code and Codex plugins run |
| `.claude-plugin/`, `.codex-plugin/`, `.agents/plugins/` | Plugin manifests and marketplace files (repo root is the plugin root) |

## Guidelines

- **Never put real personal data in code, tests, fixtures or screenshots.** Use made-up names, addresses and numbers (e.g. `Happy-ro 12`, `010-0000-0000`). Run the demo script for screenshots instead of your own report.
- Keep the package dependency-free (standard library only, Python 3.10+).
- Any new user-facing string needs both `en` and `ko` (the tests check this).
- Rubric changes should cite an official Anthropic or OpenAI source, and bump `version` in `default.json`.
- Add a test for parser changes; transcript formats change often.

## Releasing

1. Bump the version in `pyproject.toml`, `agentcoach/__init__.py`, `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (a test checks they match).
2. `claude plugin validate --strict .`
3. Publish a GitHub release tagged `vX.Y.Z`. The `Release` workflow tests, builds and uploads to PyPI through trusted publishing.

## Adding a new tool (Cursor, Gemini CLI, ...)

Write a `parse_<tool>_file(path) -> Session | None` in `collect.py` that returns only turns a human typed, then add it to `collect()`. Look at `parse_codex_file` for a compact example.
