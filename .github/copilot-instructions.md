# Token-efficient agent workflow

This repository includes `agent-tools` for reducing unnecessary command output in coding-agent context.

## Command output

- Prefer `tkrun <command>` for verbose tests, builds, linters, type checks, and similar commands when `tkrun` is installed.
- If `tkrun` is not on `PATH`, run the repository-local script:
  `python3 skills/token-efficient-debugging/scripts/tkrun.py <command>`
- Do not dump large generated logs or dependency trees into the chat when a focused summary is sufficient.
- Preserve full command output in `.agent-logs/` when the token-efficient runner captures it.

## File inspection

- Prefer `rg` for targeted code searches.
- Prefer `tkread` for focused file inspection when it is installed.
- If `tkread` is not on `PATH`, use the repository-local `tkread.py` script.
- Read only the relevant ranges of large files instead of printing entire files.

## Debugging

- Start with the smallest command that can confirm or narrow the problem.
- Use the summarized failure output from `tkrun` to identify the relevant file, line, error, and nearby context.
- Use `git diff` to inspect changes before proposing or committing them.
- Do not treat token estimates reported by agent-tools as API billing measurements.

## Runtime data

- Runtime logs and statistics belong in the project `.agent-logs/` directory.
- Do not recreate or depend on the removed `.agent-tools/` source directory.
