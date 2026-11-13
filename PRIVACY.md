# Privacy

agent-coach is a local command-line tool and plugin. It has no server, no account, no analytics and no telemetry. The maintainers receive nothing.

## What it reads

- Conversation transcripts that Claude Code and Codex already store on your computer: `~/.claude/projects/**/*.jsonl` and `~/.codex/sessions/**/*.jsonl`.
- Your own redaction list, if you create one: `~/.agent-coach/redact.txt`.

## What leaves your computer

- **LLM judge (default when the `claude` or `codex` CLI is installed):** for each conversation being graded, the prompts you typed and one-line summaries of the agent's actions are passed to that CLI, which sends them to the Claude or Codex account you are signed in to. That is the same provider your conversations already went to. API keys, tokens, emails, phone numbers, national ID and card numbers, Korean road addresses and any terms in `redact.txt` are masked first.
- **Offline mode (`--judge heuristic`):** nothing leaves your computer.

## What it stores

Results are written only to your computer: `~/.agent-coach/history/run-*.json` and `~/.agent-coach/report.html` (or `AGENT_COACH_HOME`). Delete that folder to remove everything.

## Credentials

agent-coach never reads, stores or sends your credentials. Grading runs through the `claude` or `codex` CLI, which uses its own sign-in.

## Contact

Questions or issues: https://github.com/1017toa/agent-coach/issues
