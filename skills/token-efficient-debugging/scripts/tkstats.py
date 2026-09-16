#!/usr/bin/env python3

from __future__ import annotations

import json

from collections import defaultdict

from token_utils import (
    find_repo_root,
    load_config,
)


def short_command(
    command: str,
    limit: int = 70,
) -> str:

    command = " ".join(
        command.split()
    )

    if len(command) <= limit:
        return command

    return (
        command[: limit - 1]
        + "…"
    )


def main() -> int:

    root = find_repo_root()

    config = load_config(
        root
    )

    path = (
        root
        / str(config["stats_file"])
    )

    if not path.exists():

        print(
            "No token-saver stats yet."
        )

        return 0

    records: list[dict] = []

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:

        for line in handle:

            try:
                value = json.loads(
                    line
                )

            except json.JSONDecodeError:
                continue

            if isinstance(
                value,
                dict,
            ):
                records.append(value)

    if not records:

        print(
            "No valid token-saver stats yet."
        )

        return 0

    raw = sum(
        int(
            record.get(
                "raw_estimated_tokens",
                0,
            )
        )
        for record in records
    )

    returned = sum(
        int(
            record.get(
                "returned_body_estimated_tokens",
                0,
            )
        )
        for record in records
    )

    avoided = sum(
        int(
            record.get(
                "avoided_estimated_tokens",
                0,
            )
        )
        for record in records
    )

    failed = sum(
        1
        for record in records
        if int(
            record.get(
                "exit_code",
                0,
            )
        )
        != 0
    )

    reduction = (
        avoided
        / raw
        * 100.0
        if raw
        else 0.0
    )

    by_command: dict[
        str,
        int,
    ] = defaultdict(int)

    for record in records:

        command = str(
            record.get(
                "command",
                "",
            )
        )

        by_command[command] += int(
            record.get(
                "avoided_estimated_tokens",
                0,
            )
        )

    print(
        "Token-saver statistics"
    )

    print(
        "=" * 48
    )

    print(
        f"Commands:                  "
        f"{len(records):>12,}"
    )

    print(
        f"Non-zero exits:            "
        f"{failed:>12,}"
    )

    print(
        f"Raw estimated tokens:      "
        f"{raw:>12,}"
    )

    print(
        f"Returned estimated tokens: "
        f"{returned:>12,}"
    )

    print(
        f"Avoided estimated tokens:  "
        f"{avoided:>12,}"
    )

    print(
        f"Estimated reduction:       "
        f"{reduction:>11.1f}%"
    )

    print()

    print(
        "Top commands by estimated "
        "context avoided"
    )

    print(
        "-" * 48
    )

    ranked = sorted(
        by_command.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    for (
        command,
        saved,
    ) in ranked[:10]:

        print(
            f"{saved:>10,}  "
            f"{short_command(command)}"
        )

    print()

    print(
        "These are context-size estimates, "
        "not API billing/cached-token measurements."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )