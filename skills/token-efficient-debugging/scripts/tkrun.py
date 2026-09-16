#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import os
import re
import shlex
import subprocess
import sys
import time
import uuid

from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from token_utils import (
    append_jsonl,
    estimate_tokens_from_bytes,
    estimate_tokens_from_text,
    find_repo_root,
    load_config,
)


ANSI_RE = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)


SIGNAL_RE = re.compile(
    r"(?ix)(?:"
    r"\b(?:"
    r"error|errors|failed|failure|failures|"
    r"exception|traceback|panic|fatal|"
    r"warning|warnings"
    r")\b"
    r"|\bTS\d{4}\b"
    r"|\b(?:"
    r"assertionerror|typeerror|referenceerror|"
    r"syntaxerror|timeout(?:error)?"
    r")\b"
    r"|\bCERTIFICATE_VERIFY_FAILED\b"
    r"|\bTLS\b.*\b(?:fail|error)\b"
    r"|\b\d+:\d+\s+(?:error|warning)\b"
    r")"
)


SUMMARY_RE = re.compile(
    r"(?ix)(?:"
    r"\btests?\b.*\b(?:passed|failed|skipped)\b"
    r"|\b(?:passed|failed|skipped)\b.*\btests?\b"
    r"|\b(?:"
    r"build|lint|typecheck|type check"
    r")\b.*\b(?:"
    r"failed|succeeded|success|complete|completed"
    r")\b"
    r"|\b\d+\s+(?:"
    r"passed|failed|warnings?|errors?"
    r")\b"
    r")"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a verbose command, save the complete log, "
            "and print a token-efficient result."
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=False
    )

    group.add_argument(
        "--b64",
        help="URL-safe base64 encoded shell command.",
    )

    group.add_argument(
        "--command",
        help="Shell command to execute.",
    )

    parser.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="Command after --",
    )

    return parser.parse_args()


def decode_command(
    args: argparse.Namespace,
) -> str:
    if args.b64:
        padding = "=" * (-len(args.b64) % 4)

        try:
            return base64.urlsafe_b64decode(
                args.b64 + padding
            ).decode("utf-8")

        except (
            ValueError,
            UnicodeDecodeError,
        ) as exc:
            raise SystemExit(
                f"Invalid --b64 command: {exc}"
            ) from exc

    if args.command:
        return args.command

    rest = list(args.rest)

    if rest and rest[0] == "--":
        rest = rest[1:]

    if rest:
        if os.name == "nt":
            return subprocess.list2cmdline(rest)

        return shlex.join(rest)

    raise SystemExit(
        "No command supplied. "
        "Use --b64, --command, or -- <command>."
    )


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub(
        "",
        text,
    )


def read_small_log(
    path: Path,
) -> str:
    return strip_ansi(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )


def reduce_log(
    path: Path,
    config: dict,
    exit_code: int,
) -> str:

    raw_estimate = estimate_tokens_from_bytes(
        path.stat().st_size
    )

    passthrough_tokens = int(
        config["passthrough_tokens"]
    )

    budget_tokens = int(
        config["budget_tokens"]
    )

    # Small output: don't waste time trying to optimize it.
    if raw_estimate <= passthrough_tokens:
        return read_small_log(path)

    head_limit = int(
        config["head_lines"]
    )

    tail_limit = int(
        config["tail_lines"]
    )

    before_limit = int(
        config["context_before"]
    )

    after_limit = int(
        config["context_after"]
    )

    max_signal_blocks = int(
        config["max_signal_blocks"]
    )

    head: list[tuple[int, str]] = []

    tail: deque[tuple[int, str]] = deque(
        maxlen=tail_limit
    )

    previous: deque[tuple[int, str]] = deque(
        maxlen=before_limit
    )

    selected: dict[int, str] = {}

    signal_blocks = 0
    after_remaining = 0

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:

        for line_no, raw_line in enumerate(
            handle,
            start=1,
        ):

            line = strip_ansi(
                raw_line.rstrip("\n")
            )

            item = (
                line_no,
                line,
            )

            if len(head) < head_limit:
                head.append(item)

            tail.append(item)

            is_signal = bool(
                SIGNAL_RE.search(line)
            )

            is_summary = bool(
                SUMMARY_RE.search(line)
            )

            if (
                is_signal
                and signal_blocks < max_signal_blocks
            ):

                signal_blocks += 1

                for (
                    prev_no,
                    prev_line,
                ) in previous:

                    selected.setdefault(
                        prev_no,
                        prev_line,
                    )

                selected.setdefault(
                    line_no,
                    line,
                )

                after_remaining = max(
                    after_remaining,
                    after_limit,
                )

            elif after_remaining > 0:

                selected.setdefault(
                    line_no,
                    line,
                )

                after_remaining -= 1

            if is_summary:
                selected.setdefault(
                    line_no,
                    line,
                )

            previous.append(item)

    # Always retain beginning and end.
    for line_no, line in head:
        selected.setdefault(
            line_no,
            line,
        )

    for line_no, line in tail:
        selected.setdefault(
            line_no,
            line,
        )

    ordered = sorted(
        selected.items()
    )

    out: list[str] = []

    previous_no: int | None = None

    for line_no, line in ordered:

        if (
            previous_no is not None
            and line_no > previous_no + 1
        ):
            out.append(
                f"... omitted lines "
                f"{previous_no + 1}-"
                f"{line_no - 1} ..."
            )

        out.append(line)
        previous_no = line_no

    if not out:
        out = [
            "(command produced no text output)"
        ]

    reduced = "\n".join(
        out
    ).strip()

    # Last safety layer:
    # even selected output can contain hundreds of errors.
    char_budget = max(
        1000,
        budget_tokens * 4,
    )

    if len(reduced) > char_budget:

        marker = (
            "\n"
            "... token-saver hard cap; "
            "middle omitted ..."
            "\n"
        )

        remaining = (
            char_budget
            - len(marker)
        )

        head_chars = max(
            0,
            remaining * 2 // 3,
        )

        tail_chars = max(
            0,
            remaining - head_chars,
        )

        reduced = (
            reduced[:head_chars]
            + marker
            + reduced[-tail_chars:]
        )

    return reduced


def main() -> int:

    args = parse_args()

    command = decode_command(
        args
    ).strip()

    repo_root = find_repo_root()

    config = load_config(
        repo_root
    )

    log_dir = (
        repo_root
        / str(config["log_dir"])
    )

    log_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    log_path = (
        log_dir
        / (
            f"{timestamp}-"
            f"{uuid.uuid4().hex[:8]}.log"
        )
    )

    started = time.monotonic()

    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    with log_path.open(
        "wb"
    ) as log_handle:

        try:

            process = subprocess.Popen(
                command,
                cwd=Path.cwd(),
                shell=True,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )

            exit_code = process.wait()

        except KeyboardInterrupt:

            try:
                process.terminate()
            except Exception:
                pass

            exit_code = 130

    # Best effort:
    # prevent other Unix users from reading logs.
    try:
        os.chmod(
            log_path,
            0o600,
        )
    except OSError:
        pass

    duration = (
        time.monotonic()
        - started
    )

    reduced = reduce_log(
        log_path,
        config,
        exit_code,
    )

    raw_tokens = (
        estimate_tokens_from_bytes(
            log_path.stat().st_size
        )
    )

    body_tokens = (
        estimate_tokens_from_text(
            reduced
        )
    )

    avoided_tokens = max(
        0,
        raw_tokens - body_tokens,
    )

    reduction_pct = (
        avoided_tokens
        / raw_tokens
        * 100.0
        if raw_tokens
        else 0.0
    )

    try:
        relative_log = (
            log_path.relative_to(
                repo_root
            )
        )

    except ValueError:
        relative_log = log_path

    header = (
        f"[token-saver] "
        f"exit={exit_code} "
        f"duration={duration:.2f}s\n"

        f"[token-saver] "
        f"full_log={relative_log}\n"

        f"[token-saver] "
        f"raw_estimate={raw_tokens} tokens; "
        f"returned_body_estimate="
        f"{body_tokens} tokens; "
        f"avoided_estimate="
        f"{avoided_tokens} tokens "
        f"({reduction_pct:.1f}%)\n"

        f"[token-saver] estimates are "
        f"context-size estimates, "
        f"not API billing data.\n"
    )

    if reduced:

        sys.stdout.write(
            header
            + "\n"
            + reduced.rstrip()
            + "\n"
        )

    else:
        sys.stdout.write(
            header
        )

    stats_path = (
        repo_root
        / str(config["stats_file"])
    )

    append_jsonl(
        stats_path,
        {
            "timestamp": started_at,
            "command": command,
            "exit_code": exit_code,
            "duration_seconds": round(
                duration,
                3,
            ),
            "log_path": str(
                relative_log
            ),
            "raw_bytes": (
                log_path.stat().st_size
            ),
            "raw_estimated_tokens": (
                raw_tokens
            ),
            "returned_body_estimated_tokens": (
                body_tokens
            ),
            "avoided_estimated_tokens": (
                avoided_tokens
            ),
            "reduction_percent": round(
                reduction_pct,
                2,
            ),
        },
    )

    # Important:
    # preserve original command exit status.
    return exit_code


if __name__ == "__main__":
    raise SystemExit(
        main()
    )