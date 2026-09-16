#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import os
import re
import shlex
import sys

from pathlib import Path


VERBOSE_COMMAND_RE = re.compile(
    r"(?ix)^\s*(?:"
    r"(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|build|lint|typecheck|type-check)\b"
    r"|(?:npx\s+)?(?:eslint|tsc|jest|vitest)\b"
    r"|pytest\b"
    r"|python(?:3)?\s+-m\s+(?:pytest|unittest)\b"
    r"|cargo\s+(?:test|build|check|clippy)\b"
    r"|go\s+test\b"
    r"|(?:(?:mvn|mvnw|mvnw\.cmd|\./mvnw)\s+(?:test|verify|package)\b)"
    r"|(?:(?:gradle|gradlew|gradlew\.bat|\./gradlew)\s+(?:test|build|check)\b)"
    r"|dotnet\s+(?:test|build)\b"
    r"|ruff\s+check\b"
    r"|mypy\b"
    r"|phpunit\b"
    r")"
)

SHELL_META_RE = re.compile(r"[\n\r;&|<>`]")


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def encode_command(command: str) -> str:
    return (
        base64.urlsafe_b64encode(command.encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )


def build_wrapper(tkrun: Path, encoded: str) -> str:
    if os.name == "nt":
        return f'py -3 "{tkrun}" --b64 {encoded}'
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(tkrun))} --b64 {encoded}"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if payload.get("hook_event_name") != "PreToolUse":
        return 0
    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    normalized = command.strip()

    if "tkrun.py" in normalized or SHELL_META_RE.search(normalized):
        return 0
    if not VERBOSE_COMMAND_RE.search(normalized):
        return 0

    cwd = Path(str(payload.get("cwd") or Path.cwd()))
    root = find_repo_root(cwd)
    tkrun = root / "skills" / "token-efficient-debugging" / "scripts" / "tkrun.py"

    if not tkrun.is_file():
        return 0

    rewritten = build_wrapper(tkrun, encode_command(normalized))

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

    json.dump(result, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
