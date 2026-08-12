"""Local dictation history log.

Every transcription is appended as one JSON object per line to a log file
(default ~/.wispr-flow-clone/history.jsonl), so you can review or search
what you've dictated. It's a plain local file you own - nothing is sent
anywhere.

Run this module directly to browse it:

    python history.py                # last 20 entries
    python history.py --limit 100
    python history.py --search budget
    python history.py --clear
"""

import argparse
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

DEFAULT_HISTORY_PATH = Path.home() / ".wispr-flow-clone" / "history.jsonl"


def append_entry(
    raw_text: str,
    text: str,
    duration_seconds: float,
    cleanup_backend: str,
    path: Path = DEFAULT_HISTORY_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "duration_seconds": round(duration_seconds, 2),
        "raw_text": raw_text,
        "text": text,
        "cleanup_backend": cleanup_backend,
    }
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_entries(path: Path = DEFAULT_HISTORY_PATH) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def clear(path: Path = DEFAULT_HISTORY_PATH) -> int:
    count = sum(1 for _ in read_entries(path))
    if path.exists():
        path.unlink()
    return count


def open_in_default_app(path: Path = DEFAULT_HISTORY_PATH) -> None:
    """Open the history file in whatever app the OS uses for .jsonl/text
    files, creating an empty one first if it doesn't exist yet.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)

    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def _format_entry(entry: dict) -> str:
    timestamp = entry.get("timestamp", "?")
    duration = entry.get("duration_seconds", 0)
    text = entry.get("text", "")
    return f"[{timestamp}] ({duration}s) {text}"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limit", type=int, default=20, help="show the last N entries (default: 20)")
    parser.add_argument(
        "--search", default=None, help="only show entries containing this text (case-insensitive)"
    )
    parser.add_argument(
        "--path", default=str(DEFAULT_HISTORY_PATH), help="history file location"
    )
    parser.add_argument("--clear", action="store_true", help="delete the history file")
    args = parser.parse_args()

    path = Path(args.path)

    if args.clear:
        count = clear(path)
        print(f"Cleared {count} entries from {path}")
        return

    entries = list(read_entries(path))
    if args.search:
        needle = args.search.lower()
        entries = [
            e
            for e in entries
            if needle in e.get("text", "").lower() or needle in e.get("raw_text", "").lower()
        ]

    if not entries:
        print(f"No history entries found at {path}")
        return

    for entry in entries[-args.limit :]:
        print(_format_entry(entry))


if __name__ == "__main__":
    main()
