#!/usr/bin/env python3
"""Simple Jinja2 template parser to find TemplateSyntaxError in templates/.

Usage: python3 tools/jinja_lint.py
Exits with code 0 if no syntax errors, 1 if any errors found.
"""
import sys
import os
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError


def find_templates(root="templates"):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith((".html", ".j2", ".jinja2")):
                yield os.path.join(dirpath, fn)


def main():
    base = os.path.abspath(os.getcwd())
    tpl_root = os.path.join(base, "templates")
    if not os.path.isdir(tpl_root):
        print(f"No templates/ directory found at {tpl_root}")
        sys.exit(2)

    env = Environment(loader=FileSystemLoader(tpl_root))

    errors = []
    scanned = 0
    for path in find_templates(tpl_root):
        scanned += 1
        rel = os.path.relpath(path, tpl_root)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                src = fh.read()
            # parse the source; this will raise TemplateSyntaxError on parse issues
            env.parse(src)
        except TemplateSyntaxError as e:
            errors.append((rel, str(e)))
        except Exception as e:
            errors.append((rel, f"Unexpected error: {e!r}"))

    print(f"Scanned {scanned} template files in templates/")
    if not errors:
        print("No Jinja TemplateSyntaxError found.")
        return 0

    print("Found template syntax issues:")
    for rel, msg in errors:
        print(f" - {rel}: {msg}")

    return 1


if __name__ == "__main__":
    code = main()
    sys.exit(code)
