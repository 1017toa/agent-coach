---
name: coach
description: Grade how the user prompts Claude Code and Codex, using their own local conversation history (~/.claude, ~/.codex) and a rubric built from Anthropic's and OpenAI's official guides, then coach them in chat with rewrites of prompts they actually wrote, missed responses, and rules worth adding to CLAUDE.md / AGENTS.md. Use when the user asks to review, grade, score or improve their prompting habits, asks how well they use Claude Code or Codex, or asks for their agent-coach report or progress.
argument-hint: "[--days N | --all] [--judge claude|codex|heuristic] [--lang en|ko] [--max-sessions N]"
---

# agent-coach

You run the agent-coach CLI for the user and turn its output into coaching. Answer in the user's language and pass `--lang ko` for Korean, `--lang en` otherwise.

Arguments the user gave: $ARGUMENTS

## 1. Find the command

Use the first that works (check with `--version`):

1. `agent-coach` on PATH (installed with pip, pipx or uv).
2. `uvx --from agent-coach-cli agent-coach` or `pipx run --spec agent-coach-cli agent-coach`, if `uv` or `pipx` exists (the PyPI package is `agent-coach-cli`; the command is `agent-coach`).
3. From this plugin's own files, no install needed. The plugin root holds the `agentcoach` package; it is `${CLAUDE_PLUGIN_ROOT}`, or, if that placeholder was not filled in, the directory two levels above this SKILL.md. Run `python -m agentcoach` (or `python3`, `py -3` on Windows) with `PYTHONPATH` set to the plugin root, e.g. `PYTHONPATH="<plugin root>" python3 -m agentcoach --version`. Needs Python 3.10+, no other dependencies.

Below, `agent-coach` means whichever form worked.

## 2. Preview

Run `agent-coach scan` with the user's window options (`--days`, `--all`, `--source`). Tell the user in one or two lines how many conversations will be graded (at most `--max-sessions`, default 20), and that each is one judge call through their own signed-in `claude` or `codex` CLI, where masked prompts and one-line action summaries are sent. Offline grading is `--judge heuristic`.

If the user already asked plainly to grade, go on. Otherwise ask once before grading.

## 3. Grade

Run `agent-coach run --no-open` plus the user's options. It takes about a minute per conversation, three at a time, so run it in the background if you can and tell the user it has started. Don't re-run it while it is going.

If it reports that nothing new was found, offer `--days 30` or `--all`.

## 4. Coach

Run `agent-coach summary` (add `--lang`). From its output, tell the user:

- The overall score and the three weakest habits, one line each.
- Two or three rewrites: what they wrote, the better version, and why. Keep their wording; don't invent examples.
- Missed responses caused by a gap in their prompt, and the "one missing piece" for each.
- Rules worth adding, with where each belongs (CLAUDE.md / AGENTS.md, memory, skill, hook). Offer to add a rule to the right file, and only edit a file after the user says yes.

Finish with the report path it printed (`~/.agent-coach/report.html`) and offer to open it. Suggest running this again in a week or two; only new conversations are graded and the trend builds up.

Other commands: `agent-coach history` (score table per run), `agent-coach report` (rebuild the HTML).

## Privacy

Prompts in the output may contain the user's personal details. Quote only what the coaching needs, and never send the output anywhere else. To mask names, the user can list them one per line in `~/.agent-coach/redact.txt`.
