<!-- agent-tools:start -->
# Token-efficient agent workflow

This project uses `agent-tools` to reduce unnecessary command output in coding-agent context.

## Command output

- Prefer `tkrun` for verbose tests, builds, linters, type checks, and similar commands when installed.
- If `tkrun` is not on `PATH`, use `python3 skills/token-efficient-debugging/scripts/tkrun.py -- <command>` from the repository root.
- Avoid dumping large generated logs, dependency trees, or complete command output into context when a focused summary is sufficient.
- Preserve full command output in `.agent-logs/` when the token-efficient runner captures it.

## File inspection

- Prefer `rg` for targeted searches.
- Prefer `tkread` for focused inspection when installed.
- If `tkread` is not on `PATH`, use `python3 skills/token-efficient-debugging/scripts/tkread.py` from the repository root.
- Read relevant ranges of large files instead of printing entire files.

## Debugging

- Start with the smallest command that can confirm or narrow the problem.
- Use the summarized failure output from `tkrun` to identify the relevant file, line, error, and nearby context.
- Use `git diff` to inspect changes before proposing or committing them.
- Use `jq` for targeted extraction from large JSON files.
- Token estimates from agent-tools are estimates of context size avoided, not API billing measurements.

## Runtime data

- Runtime logs and statistics belong in the project `.agent-logs/` directory.
- Do not recreate or depend on the removed `.agent-tools/` source directory.
<!-- agent-tools:end -->
