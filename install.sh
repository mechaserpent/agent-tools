#!/usr/bin/env bash
set -euo pipefail

# Install agent-tools from the directory containing this script.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${AGENT_TOOLS_INSTALL_DIR:-$HOME/.local/share/agent-tools}"
BIN_DIR="${AGENT_TOOLS_BIN_DIR:-$HOME/.local/bin}"
SKILL_DIR="${AGENT_TOOLS_SKILL_DIR:-$HOME/.agents/skills/token-efficient-debugging}"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
PROJECT_DIR="${AGENT_TOOLS_PROJECT_DIR:-$(pwd)}"
COPILOT_FILE="$PROJECT_DIR/.github/copilot-instructions.md"
COPILOT_SOURCE="$INSTALL_DIR/adapters/vscode-copilot/copilot-instructions.md"

mkdir -p "$(dirname "$INSTALL_DIR")" "$BIN_DIR" "$(dirname "$SKILL_DIR")" "$CODEX_DIR"

if [ -e "$INSTALL_DIR" ] && [ ! -L "$INSTALL_DIR" ]; then
  echo "Refusing to replace existing non-symlink: $INSTALL_DIR" >&2
  exit 1
fi
ln -sfn "$ROOT" "$INSTALL_DIR"

ln -sfn "$INSTALL_DIR/skills/token-efficient-debugging/scripts/tkrun.py" "$BIN_DIR/tkrun"
ln -sfn "$INSTALL_DIR/skills/token-efficient-debugging/scripts/tkread.py" "$BIN_DIR/tkread"
ln -sfn "$INSTALL_DIR/skills/token-efficient-debugging/scripts/tkstats.py" "$BIN_DIR/tkstats"

if [ -e "$SKILL_DIR" ] && [ ! -L "$SKILL_DIR" ]; then
  echo "Refusing to replace existing non-symlink skill: $SKILL_DIR" >&2
  exit 1
fi
ln -sfn "$INSTALL_DIR/skills/token-efficient-debugging" "$SKILL_DIR"

HOOKS_FILE="$CODEX_DIR/hooks.json"
HOOK_COMMAND="python3 \"$INSTALL_DIR/adapters/codex/hooks/token_saver.py\""

python3 - "$HOOKS_FILE" "$HOOK_COMMAND" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
command = sys.argv[2]

if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Cannot parse existing Codex hooks file: {path}: {exc}")
else:
    data = {}

hooks = data.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])

# Replace only a token-saver hook previously installed by this project.
pre[:] = [
    item
    for item in pre
    if not (
        isinstance(item, dict)
        and item.get("matcher") == "^Bash$"
        and any(
            isinstance(h, dict)
            and "token_saver.py" in str(h.get("command", ""))
            for h in item.get("hooks", [])
        )
    )
]

pre.append(
    {
        "matcher": "^Bash$",
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 10,
                "statusMessage": "Checking whether command output should be reduced",
            }
        ],
    }
)

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

# Install project-level VS Code Copilot instructions without overwriting user content.
mkdir -p "$(dirname "$COPILOT_FILE")"
python3 - "$COPILOT_FILE" "$COPILOT_SOURCE" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
source = pathlib.Path(sys.argv[2])
start = "<!-- agent-tools:start -->"
end = "<!-- agent-tools:end -->"
block = start + "\n" + source.read_text(encoding="utf-8").strip() + "\n" + end

if path.exists():
    text = path.read_text(encoding="utf-8")
else:
    text = ""

if start in text and end in text:
    before = text.split(start, 1)[0].rstrip()
    after = text.split(end, 1)[1].lstrip()
    text = (before + "\n\n" if before else "") + block + ("\n\n" + after if after else "")
else:
    text = text.rstrip()
    text = (text + "\n\n" if text else "") + block + "\n"

path.write_text(text, encoding="utf-8")
PY

chmod +x "$INSTALL_DIR/skills/token-efficient-debugging/scripts/"*.py

echo
cat <<MSG
Installed agent-tools.

Source:
  $INSTALL_DIR -> $ROOT

CLI commands:
  $BIN_DIR/tkrun
  $BIN_DIR/tkread
  $BIN_DIR/tkstats

Skill:
  $SKILL_DIR

Codex hooks:
  $HOOKS_FILE

VS Code Copilot instructions:
  $COPILOT_FILE

Make sure $BIN_DIR is in PATH.
MSG
