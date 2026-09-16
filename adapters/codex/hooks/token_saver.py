#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import os
import re
import shlex
import sys

from pathlib import Path


# Only automatically wrap simple commands that are
# commonly verbose.
#
# Composite shell expressions are intentionally ignored.
VERBOSE_COMMAND_RE = re.compile(
    r"(?ix)^\s*(?:"

    r"(?:npm|pnpm|yarn|bun)\s+"
    r"(?:run\s+)?"
    r"(?:"
    r"test|build|lint|typecheck|type-check"
    r")\b"

    r"|(?:npx\s+)?"
    r"(?:"
    r"eslint|tsc|jest|vitest"
    r")\b"

    r"|pytest\b"

    r"|python(?:3)?\s+-m\s+"
    r"(?:pytest|unittest)\b"

    r"|cargo\s+"
    r"(?:"
    r"test|build|check|clippy"
    r")\b"

    r"|go\s+test\b"

    r"|(?:"
    r"mvn|mvnw|mvnw\.cmd|"
    r"\./mvnw"
    r")\s+"
    r"(?:"
    r"test|verify|package"
    r")\b"

    r"|(?:"
    r"gradle|gradlew|gradlew\.bat|"
    r"\./gradlew"
    r")\s+"
    r"(?:"
    r"test|build|check"
    r")\b"

    r"|dotnet\s+"
    r"(?:"
    r"test|build"
    r")\b"

    r"|ruff\s+check\b"

    r"|mypy\b"

    r"|phpunit\b"

    r")"
)


# We deliberately refuse to rewrite compound shell commands.
#
# Example:
#
# npm test && npm build
# npm test | tee output.log
# command > file
#
# This avoids accidentally changing shell semantics.
SHELL_META_RE = re.compile(
    r"[\n\r;&|<>`]"
)


def find_repo_root(
    start: Path,
) -> Path:

    current = start.resolve()

    for candidate in (
        current,
        *current.parents,
    ):

        if (
            candidate
            / ".git"
        ).exists():

            return candidate

    return current


def encode_command(
    command: str,
) -> str:

    encoded = (
        base64.urlsafe_b64encode(
            command.encode(
                "utf-8"
            )
        )
        .decode("ascii")
        .rstrip("=")
    )

    return encoded


def build_wrapper(
    tkrun: Path,
    encoded: str,
) -> str:

    if os.name == "nt":

        # hooks.json launches this hook using `py -3`,
        # therefore the Windows Python launcher should
        # already be available.
        #
        # Base64 means we don't have to re-escape the
        # original command through another shell layer.
        return (
            f'py -3 "{tkrun}" '
            f"--b64 {encoded}"
        )

    return (
        f"{shlex.quote(sys.executable)} "
        f"{shlex.quote(str(tkrun))} "
        f"--b64 {encoded}"
    )


def main() -> int:

    try:
        payload = json.load(
            sys.stdin
        )

    except json.JSONDecodeError:
        # Hook failure should not break normal Codex usage.
        return 0

    if (
        payload.get(
            "hook_event_name"
        )
        != "PreToolUse"
    ):
        return 0

    if (
        payload.get(
            "tool_name"
        )
        != "Bash"
    ):
        return 0

    tool_input = payload.get(
        "tool_input"
    )

    if not isinstance(
        tool_input,
        dict,
    ):
        return 0

    command = tool_input.get(
        "command"
    )

    if (
        not isinstance(
            command,
            str,
        )
        or not command.strip()
    ):
        return 0

    normalized = command.strip()

    # Prevent accidental wrapper loops.
    if "tkrun.py" in normalized:
        return 0

    # Don't alter shell pipelines, redirection,
    # compound commands, etc.
    if SHELL_META_RE.search(
        normalized
    ):
        return 0

    if not VERBOSE_COMMAND_RE.search(
        normalized
    ):
        return 0

    cwd = Path(
        str(
            payload.get("cwd")
            or Path.cwd()
        )
    )

    root = find_repo_root(
        cwd
    )

    tkrun = (
        root
        / ".agent-tools"
        / "tkrun.py"
    )

    if not tkrun.is_file():
        return 0

    encoded = encode_command(
        normalized
    )

    rewritten = build_wrapper(
        tkrun,
        encoded,
    )

    # Current Codex PreToolUse rewrite contract:
    #
    # permissionDecision = allow
    # updatedInput.command = replacement Bash command
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {
                **tool_input,
                "command": rewritten,
            },
        }
    }

    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )