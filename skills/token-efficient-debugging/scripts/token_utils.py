from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "budget_tokens": 2500,
    "passthrough_tokens": 1200,
    "head_lines": 20,
    "tail_lines": 40,
    "context_before": 3,
    "context_after": 8,
    "max_signal_blocks": 80,
    "log_dir": ".agent-logs",
    "stats_file": ".agent-logs/stats.jsonl",
}


def find_repo_root(start: Path | None = None) -> Path:
    """Find the nearest parent directory containing .git."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def load_config(repo_root: Path) -> dict[str, Any]:
    """Load the skill's config and merge it with defaults."""
    config = dict(DEFAULT_CONFIG)
    path = Path(__file__).resolve().parent / "config.json"

    if not path.exists():
        return config

    try:
        user_config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return config

    if isinstance(user_config, dict):
        config.update(user_config)

    return config


def estimate_tokens_from_text(text: str) -> int:
    """Approximate context tokens; this is not API billing data."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def estimate_tokens_from_bytes(size: int) -> int:
    """Approximate tokens from byte size for rough output statistics."""
    if size <= 0:
        return 0
    return max(1, math.ceil(size / 4))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
