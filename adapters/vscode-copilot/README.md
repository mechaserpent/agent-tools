# VS Code Copilot adapter

The VS Code Copilot integration is intentionally project-level: the installer installs a reusable instruction file into the repository's `.github/copilot-instructions.md`.

The instructions teach Copilot to use the shared `agent-tools` CLI (`tkrun`, `tkread`, and `tkstats`) when available, while falling back to the repository-local scripts.

No separate copy of the token-efficient-debugging core is maintained here.

## Installation

Run the repository root installer:

```bash
./install.sh
```

If you want to install the instructions into a different project, set `AGENT_TOOLS_PROJECT_DIR`:

```bash
AGENT_TOOLS_PROJECT_DIR=/path/to/project ./install.sh
```

The installer creates or updates:

```text
/path/to/project/.github/copilot-instructions.md
```

Existing Copilot instruction content is preserved when the file does not contain an agent-tools managed block. When a managed block exists, only that block is replaced.

## Why project-level instructions?

VS Code Copilot works with repository instructions, so project-level configuration avoids modifying unrelated global VS Code settings and makes the behavior visible and versionable with the project.

The adapter does not assume that every VS Code/Copilot version exposes the same hook API. Automatic command interception remains a Codex-specific integration; Copilot receives the shared workflow instructions and can explicitly invoke the same core tools.
