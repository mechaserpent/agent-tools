# agent-tools

Reusable tools and agent integrations for token-efficient software development.

The repository keeps three layers separate:

- `skills/` — reusable agent skills and their executable scripts.
- `adapters/` — agent-specific integrations such as Codex hooks and VS Code Copilot instructions.
- `AGENTS.md` — instructions for agents working inside this repository.

## Quick start

### macOS / Linux / Git Bash

Clone the repository and run the installer:

```bash
git clone https://github.com/mechaserpent/agent-tools.git
cd agent-tools
./install.sh
```

### Windows PowerShell

Clone the repository and run the Windows installer:

```powershell
git clone https://github.com/mechaserpent/agent-tools.git
cd agent-tools
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

The installer is designed to work from the cloned directory. It does **not** depend on a `.agent-tools/` directory inside the clone.

By default, `install.sh` and `install.ps1` install the shared CLI/skill, configure the Codex hook, and add the managed VS Code Copilot instructions to the project from which the installer was run.

## Installation locations

### macOS / Linux

By default, `install.sh` creates the following links/files:

| Purpose | Default location |
|---|---|
| Installed repository | `~/.local/share/agent-tools` |
| CLI: `tkrun` | `~/.local/bin/tkrun` |
| CLI: `tkread` | `~/.local/bin/tkread` |
| CLI: `tkstats` | `~/.local/bin/tkstats` |
| Shared skill | `~/.agents/skills/token-efficient-debugging` |
| Codex hooks | `~/.codex/hooks.json` |
| VS Code Copilot instructions | `<project>/.github/copilot-instructions.md` |

### Windows

By default, `install.ps1` uses:

| Purpose | Default location |
|---|---|
| Installed repository | `%USERPROFILE%\.local\share\agent-tools` |
| CLI commands | `%USERPROFILE%\.local\bin\tkrun.cmd`, `tkread.cmd`, `tkstats.cmd` |
| Shared skill | `%USERPROFILE%\.agents\skills\token-efficient-debugging` |
| Codex hooks | `%USERPROFILE%\.codex\hooks.json` |
| VS Code Copilot instructions | `<project>\.github\copilot-instructions.md` |

The Windows installer uses directory junctions where possible, with a copy fallback if the environment blocks junction creation. The CLI commands are `.cmd` wrappers so they work from both PowerShell and Command Prompt.

After installation, add `%USERPROFILE%\.local\bin` to your user `PATH` if it is not already present, then restart your terminal/VS Code.

## VS Code Copilot

The VS Code Copilot integration is project-level and uses `.github/copilot-instructions.md`. It teaches Copilot to use the same `tkrun`, `tkread`, and `tkstats` tools as the other agents.

The installers write a managed block into the project from which they are run. Existing content in `.github/copilot-instructions.md` is preserved; only an existing `agent-tools` managed block is replaced on subsequent installs.

For example, to install agent-tools into one project while keeping the toolkit repository elsewhere:

```bash
cd /path/to/my-project
/path/to/agent-tools/install.sh
```

On Windows PowerShell:

```powershell
cd C:\path\to\my-project
C:\path\to\agent-tools\install.ps1
```

Or explicitly select the target project with the environment variable:

```powershell
$env:AGENT_TOOLS_PROJECT_DIR = 'C:\path\to\my-project'
C:\path\to\agent-tools\install.ps1
```

The adapter deliberately does not assume a particular VS Code/Copilot hook API. Codex gets automatic Bash interception through its hook adapter; Copilot gets portable repository instructions and can invoke the same core CLI tools explicitly.

See `adapters/vscode-copilot/README.md` for adapter-specific details.

## Runtime files

The tools intentionally keep runtime data separate from the source repository:

- Command logs: `.agent-logs/` in the project where `tkrun` is executed.
- Token statistics: `.agent-logs/stats.jsonl` in that project.

These paths are runtime data, not installation paths. They are ignored by Git by default.

The configuration shipped with the skill lives at:

```text
skills/token-efficient-debugging/scripts/config.json
```

It controls output budgets and runtime log/stat locations.

## CLI usage

After installation, make sure the relevant bin directory is on `PATH`.

Run a verbose command through the reducer:

```text
tkrun -- npm test
tkrun -- npm run build
tkrun -- pytest
```

Read only the useful part of a large file:

```text
tkread src/example.ts --lines 100:220
tkread src/example.ts --grep "fetchWeather"
```

View token-saver statistics:

```text
tkstats
```

The reported token numbers are estimates of context size avoided. They are **not** API billing measurements.

## Codex integration

The installer registers a Codex `PreToolUse` hook in:

```text
~/.codex/hooks.json
```

On Windows the corresponding default is `%USERPROFILE%\.codex\hooks.json`, and the hook includes a Windows command that uses the Python launcher (`py -3`).

The hook points at the installed copy of `token_saver.py` and automatically wraps supported verbose Bash commands with `tkrun`. It deliberately leaves compound shell commands and unrelated short commands alone.

## Custom installation locations

### macOS / Linux

The shell installer supports environment variables:

```bash
AGENT_TOOLS_INSTALL_DIR="$HOME/tools/agent-tools" \
AGENT_TOOLS_BIN_DIR="$HOME/bin" \
AGENT_TOOLS_SKILL_DIR="$HOME/.agents/skills/token-efficient-debugging" \
CODEX_HOME="$HOME/.codex" \
AGENT_TOOLS_PROJECT_DIR="$HOME/projects/my-app" \
./install.sh
```

### Windows PowerShell

The PowerShell installer uses the same environment variable names:

```powershell
$env:AGENT_TOOLS_INSTALL_DIR = "$HOME\tools\agent-tools"
$env:AGENT_TOOLS_BIN_DIR = "$HOME\bin"
$env:AGENT_TOOLS_SKILL_DIR = "$HOME\.agents\skills\token-efficient-debugging"
$env:CODEX_HOME = "$HOME\.codex"
$env:AGENT_TOOLS_PROJECT_DIR = "$HOME\projects\my-app"
.\install.ps1
```

All variables are optional. `AGENT_TOOLS_PROJECT_DIR` controls where the VS Code Copilot instruction file is installed and defaults to the current working directory.

## Repository layout

```text
agent-tools/
├── AGENTS.md
├── CHANGELOG.md
├── README.md
├── install.sh
├── install.ps1
├── adapters/
│   ├── codex/
│   │   ├── hooks.json
│   │   └── hooks/
│   │       └── token_saver.py
│   └── vscode-copilot/
│       ├── README.md
│       └── copilot-instructions.md
├── .github/
│   └── copilot-instructions.md
└── skills/
    └── token-efficient-debugging/
        ├── SKILL.md
        └── scripts/
            ├── config.json
            ├── tkread.py
            ├── tkrun.py
            ├── tkstats.py
            └── token_utils.py
```

## Development

The repository itself does not require a `.agent-tools/` source directory. Keep reusable implementation code under `skills/` and agent-specific integration under `adapters/`.

When editing the tools, run the Python files directly or through the installed commands and verify that no source/configuration file refers to the removed `.agent-tools/` source directory.
