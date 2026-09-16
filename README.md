# agent-tools

Reusable tools and agent integrations for token-efficient software development.

The repository keeps three layers separate:

- `skills/` — reusable agent skills and their executable scripts.
- `adapters/` — agent-specific integrations such as Codex hooks.
- `AGENTS.md` — instructions for agents working inside this repository.

## Quick start

Clone the repository and run the installer:

```bash
git clone https://github.com/mechaserpent/agent-tools.git
cd agent-tools
./install.sh
```

The installer is designed to work from the cloned directory. It does **not** depend on a `.agent-tools/` directory inside the clone.

## Installation locations

By default, `install.sh` creates the following links/files:

| Purpose | Default location |
|---|---|
| Installed repository | `~/.local/share/agent-tools` |
| CLI: `tkrun` | `~/.local/bin/tkrun` |
| CLI: `tkread` | `~/.local/bin/tkread` |
| CLI: `tkstats` | `~/.local/bin/tkstats` |
| Shared skill | `~/.agents/skills/token-efficient-debugging` |
| Codex hooks | `~/.codex/hooks.json` |

The installed repository is a symlink to the clone, so `git pull` updates the installed tools without copying files around.

The shared skill is also a symlink to the installed repository. This allows Codex and other compatible agent tooling to use the same skill without maintaining another copy.

## Runtime files

The tools intentionally keep runtime data separate from the source repository:

- Command logs: `.agent-logs/` in the project where `tkrun` is executed.
- Token statistics: `.agent-tools/stats.jsonl` in that project.

These paths are runtime data, not installation paths. They are ignored by Git by default.

The configuration shipped with the skill lives at:

```text
skills/token-efficient-debugging/scripts/config.json
```

It controls output budgets and runtime log/stat locations.

## CLI usage

After installation, make sure `~/.local/bin` is on `PATH`.

Run a verbose command through the reducer:

```bash
tkrun -- npm test
tkrun -- npm run build
tkrun -- pytest
```

Read only the useful part of a large file:

```bash
tkread src/example.ts --lines 100:220
tkread src/example.ts --grep "fetchWeather"
```

View token-saver statistics:

```bash
tkstats
```

The reported token numbers are estimates of context size avoided. They are **not** API billing measurements.

## Codex integration

The installer registers a Codex `PreToolUse` hook in:

```text
~/.codex/hooks.json
```

The hook points at the installed copy of:

```text
~/.local/share/agent-tools/adapters/codex/hooks/token_saver.py
```

The hook automatically wraps supported verbose Bash commands with `tkrun`. It deliberately leaves compound shell commands and unrelated short commands alone.

## Custom installation locations

The installer supports environment variables when the defaults are not suitable:

```bash
AGENT_TOOLS_INSTALL_DIR="$HOME/tools/agent-tools" \
AGENT_TOOLS_BIN_DIR="$HOME/bin" \
AGENT_TOOLS_SKILL_DIR="$HOME/.agents/skills/token-efficient-debugging" \
CODEX_HOME="$HOME/.codex" \
./install.sh
```

All variables are optional.

## Repository layout

```text
agent-tools/
├── AGENTS.md
├── CHANGELOG.md
├── README.md
├── install.sh
├── adapters/
│   └── codex/
│       ├── hooks.json
│       └── hooks/
│           └── token_saver.py
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

When editing the tools, run the Python files directly or through the installed symlinks and verify that no source/configuration file refers to the removed `.agent-tools/` source directory.
