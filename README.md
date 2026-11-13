# agent-coach

**English** | [한국어](README.ko.md)

**A personal coach for how you direct Claude Code and Codex, built from your own conversation history.**

agent-coach grades the conversations already sitting in `~/.claude` and `~/.codex` against the official guidance Anthropic and OpenAI publish. It shows which habits you tend to skip, rewrites the prompts you actually wrote into better versions, and finds the moments where you didn't get what you wanted. Run it again every week or two: only the new conversations are graded, so you can see whether you're improving.

## Why

- **Grounded in the official guides.** Every habit links to the guide section it comes from ([rubric](agentcoach/rubric/default.json)).
- **Coaching from your own conversations.** Real rewrites of what you typed, not generic tips.
- **Short prompts aren't penalized.** In a long conversation, "ok do it" is often all that's needed. Coaching targets the turns that actually missed, and only when the cause was a gap in your prompt.
- **Progress over time.** Each run is saved under `~/.agent-coach/history/`, so your trend survives even after the tools delete old transcripts.
- **Claude Code and Codex on one scale.** Both tools in one report.
- **No API key.** Grading runs through the `claude` or `codex` CLI you're already signed in to. Without either, it falls back to offline keyword scoring.
- **Local first.** Secrets and contact details are masked before anything is sent to the judge, and results stay on your machine. Pure Python standard library, no dependencies.

## Install and run

Requires Python 3.9+.

```bash
pip install git+https://github.com/1017toa/agent-coach.git
```

```bash
agent-coach scan        # preview which conversations would be graded (no model calls)
agent-coach run         # grade → save the run → open the report
agent-coach history     # score table per run
agent-coach report      # rebuild the report from saved runs
```

To run from a checkout without installing: `python -m agentcoach run`.

Common options:

- `--days 30` / `--all`: time window (default: since the previous run; 14 days on the first run)
- `--judge claude|codex|heuristic`: which judge (default auto)
- `--model sonnet`: judge model
- `--max-sessions 20`: max conversations to grade; each one costs one model call
- `--source claude` / `--source codex`: only one tool
- `--rubric my-rubric.json`: your own rubric for a course or team
- `--lang en|ko`: language of the report and coaching (default: your OS locale; also `AGENT_COACH_LANG`)

## The report

One screen, five tabs. Each pane scrolls on its own, and on phones the list and detail stack.

- **Overview**: overall score, the three habits to focus on, radar chart, weakest-first bars
- **Coaching**: habits on the left; on the right, rewrites from your conversations, the official guidance, and the conversations that missed it
- **Missed responses**: where you didn't get what you wanted, split by cause (below); recurring gaps grouped into rule candidates
- **Conversations**: search and filter; per-conversation verdicts and rewrites
- **Progress**: trend per habit across runs

## Missed-response analysis

Context builds up over a conversation, so a short instruction can be exactly right. agent-coach never marks a prompt down for being short. It looks for **turns that didn't get what you wanted**, judged by what happened next:

- **Signals**: you corrected the result, repeated an earlier instruction, asked to redo or undo, reported damage, showed frustration, or the agent had to ask back.
- **Causes**: *gap in your prompt* (something only you knew was missing and context didn't cover it) / *agent error* (context was enough) / *changed your mind* / *external limit*.
- **Coaching**: only prompt gaps get a rewrite, phrased as "the one missing piece". Gaps that recur across conversations are grouped, with a one-line rule and where it belongs: CLAUDE.md/AGENTS.md, memory, a skill, or a hook.
- Causes are classified only with an LLM judge; keyword scoring finds the signals and leaves the cause unclassified.

## The 11 habits (rubric v2)

| Habit | What the guides recommend |
|---|---|
| Specific context | State the goal and point at the file, screen and symptom from the start |
| Done criteria and verification | Give a pass/fail check (tests, build, screenshot) and let the agent run it |
| Constraints and preferences | Say what must not change and which approach you prefer |
| Hand over the real material | Attach the @file, screenshot or full error instead of describing it |
| Scope and output shape | Minimal or full version; format and length of the result |
| Plan or interview first | For big or fuzzy work, plan or get interviewed before building |
| Stop points and working style | How far to go alone, where to stop and ask, how to report |
| Ask for evidence, review the result | Commands, output, diff; a fresh session to review |
| Course correction | After two failed corrections, start fresh with a better prompt |
| Move repeated rules into files | Put recurring rules in CLAUDE.md, AGENTS.md or a skill |
| One outcome per conversation | New work in a new conversation; tidy long ones |

### Sources

- Anthropic: [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices), [Getting the most out of Opus 5.5](https://claude.dev/blog/getting-the-most-out-of-opus-5-5/)
- Claude Academy: [AI Fluency: Framework & Foundations](https://academy.claude.com/courses/ai-fluency-framework-foundations), [Claude Code 101](https://academy.claude.com/courses/claude-code-101), [Claude Code in Action](https://academy.claude.com/courses/claude-code-in-action), [Claude 101](https://academy.claude.com/courses/claude-101)
- OpenAI: [Codex Best practices](https://learn.chatgpt.com/guides/best-practices), [Codex Prompting](https://learn.chatgpt.com/docs/prompting)
- OpenAI Academy: [Get Started with Codex](https://academy.openai.com/public/courses/get-started-with-codex-jkhsq), [Agents and Workflows](https://academy.openai.com/public/courses/agents-and-workflows-y0qoc), [Extend Codex Workflows](https://academy.openai.com/public/courses/extend-codex-workflows-4e61p) (course bodies need sign-in; only the public overviews are used)

When the rubric changes, earlier runs have no score for new habits and the report says the versions differ.

## Grading on a schedule

Run `agent-coach run` every week or two; each run grades only what's new and adds to the trend. Claude Code deletes transcripts older than 30 days by default, so keep the interval shorter than that.

## Privacy

- Raw transcripts never leave your machine. With an LLM judge, the conversation's prompts (masked) and one-line summaries of the agent's actions are sent to the Claude or Codex account you're signed in to. Use `--judge heuristic` to avoid that.
- Scripted `claude -p` / `codex exec` runs and app-generated messages are excluded by default.
- Keys, tokens, emails, phone numbers, national ID and card numbers, and Korean road addresses are masked automatically. Names can't be detected reliably, so list yours (name, romanized name, company…) one per line in `~/.agent-coach/redact.txt`.

## Development

```bash
python -m unittest discover -s tests
```

Roadmap: anonymized aggregate export for courses, example custom rubrics, Cursor and Gemini CLI support.

## License

MIT
