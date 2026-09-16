#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re

from pathlib import Path

from token_utils import (
    estimate_tokens_from_text,
)


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Read only the useful portion "
            "of a potentially large text/source file."
        )
    )

    parser.add_argument(
        "path",
        type=Path,
    )

    parser.add_argument(
        "--lines",
        help=(
            "1-based inclusive range, "
            "for example 120:220"
        ),
    )

    parser.add_argument(
        "--grep",
        help="Regex to search for",
    )

    parser.add_argument(
        "--context",
        type=int,
        default=4,
        help=(
            "Context lines around --grep matches"
        ),
    )

    parser.add_argument(
        "--max-lines",
        type=int,
        default=240,
        help="Maximum lines returned",
    )

    return parser.parse_args()


def parse_line_range(
    value: str,
    total: int,
) -> tuple[int, int]:

    match = re.fullmatch(
        r"(\d+)(?::(\d+))?",
        value.strip(),
    )

    if not match:
        raise SystemExit(
            "--lines must look like "
            "START:END or LINE"
        )

    start = int(
        match.group(1)
    )

    end = int(
        match.group(2)
        or start
    )

    if (
        start < 1
        or end < start
    ):
        raise SystemExit(
            "Invalid --lines range"
        )

    return (
        start,
        min(
            end,
            total,
        ),
    )


def render(
    numbered: list[tuple[int, str]],
) -> str:

    if not numbered:
        return "(no matching lines)"

    width = len(
        str(numbered[-1][0])
    )

    out: list[str] = []

    previous: int | None = None

    for line_no, line in numbered:

        if (
            previous is not None
            and line_no > previous + 1
        ):
            out.append("...")

        out.append(
            f"{line_no:>{width}} | {line}"
        )

        previous = line_no

    return "\n".join(out)


def main() -> int:

    args = parse_args()

    path = args.path.resolve()

    if not path.is_file():
        raise SystemExit(
            f"File not found: {path}"
        )

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = text.splitlines()

    total = len(lines)

    selected: dict[int, str] = {}

    if args.lines:

        start, end = parse_line_range(
            args.lines,
            total,
        )

        for idx in range(
            start,
            end + 1,
        ):
            selected[idx] = (
                lines[idx - 1]
            )

    elif args.grep:

        try:
            pattern = re.compile(
                args.grep,
                re.IGNORECASE,
            )

        except re.error as exc:

            raise SystemExit(
                f"Invalid --grep regex: {exc}"
            ) from exc

        for idx, line in enumerate(
            lines,
            start=1,
        ):

            if pattern.search(line):

                lo = max(
                    1,
                    idx - args.context,
                )

                hi = min(
                    total,
                    idx + args.context,
                )

                for line_no in range(
                    lo,
                    hi + 1,
                ):
                    selected[line_no] = (
                        lines[line_no - 1]
                    )

    elif total <= args.max_lines:

        for idx, line in enumerate(
            lines,
            start=1,
        ):
            selected[idx] = line

    else:

        head_count = min(
            80,
            args.max_lines * 2 // 3,
        )

        tail_count = min(
            40,
            args.max_lines - head_count,
        )

        for idx in range(
            1,
            head_count + 1,
        ):
            selected[idx] = (
                lines[idx - 1]
            )

        tail_start = max(
            1,
            total - tail_count + 1,
        )

        for idx in range(
            tail_start,
            total + 1,
        ):
            selected[idx] = (
                lines[idx - 1]
            )

    ordered = sorted(
        selected.items()
    )[: args.max_lines]

    body = render(
        ordered
    )

    print(
        f"[tkread] file={path}"
    )

    print(
        f"[tkread] total_lines={total}; "
        f"file_estimate="
        f"{estimate_tokens_from_text(text)} "
        f"tokens"
    )

    if (
        not args.lines
        and not args.grep
        and total > args.max_lines
    ):

        print(
            "[tkread] large file: "
            "showing head/tail only; "
            "use --lines or --grep "
            "for a focused read"
        )

    print()

    print(body)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )