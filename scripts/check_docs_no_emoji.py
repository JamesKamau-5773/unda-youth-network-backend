#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


def iter_docs_files():
    yield ROOT / "README.md"
    docs_dir = ROOT / "documentations"
    for file_path in docs_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".md", ".txt"}:
            yield file_path


def main() -> int:
    violations = []

    for file_path in iter_docs_files():
        if not file_path.exists():
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if EMOJI_RE.search(line):
                violations.append((file_path.relative_to(ROOT), line_number, line.strip()))

    if violations:
        print("FAIL: Emoji characters found in documentation files.")
        for relative_path, line_number, line in violations:
            print(f"- {relative_path}:{line_number}: {line}")
        return 1

    print("PASS: No emoji characters found in README/documentations files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
