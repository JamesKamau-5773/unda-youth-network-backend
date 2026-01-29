#!/usr/bin/env python3
"""CI lint: fail if broad csrf exemptions are present.

Usage: python3 tools/ci_csrf_lint.py
Exits 1 if any forbidden patterns are found.
"""
import re
import sys
from pathlib import Path

FORBIDDEN = [
    r"csrf\.exempt\(\s*api_bp\s*\)",
]

root = Path(__file__).resolve().parents[1]
matches = []
for p in root.rglob('*.py'):
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        continue
    for pat in FORBIDDEN:
        if re.search(pat, txt):
            matches.append((str(p.relative_to(root)), pat))

if matches:
    print('Forbidden csrf.exempt usage found:')
    for f, pat in matches:
        print(f' - {f}: matched {pat}')
    sys.exit(1)
print('No forbidden csrf.exempt patterns found.')
sys.exit(0)
