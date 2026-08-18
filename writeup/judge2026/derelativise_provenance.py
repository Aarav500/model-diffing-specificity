"""Rewrite absolute local paths in provenance records as repo-relative.

Why this is a fix and not tampering: the absolute path names *this machine's
checkout*, not anything about the model that was diffed. `results/artifacts/L00/
_merged_b` is the same referent, is reproducible on another machine, and does
not embed a username. Nothing about the provenance claim changes.

Why it matters beyond tidiness: these files are machine-generated, so nobody
thinks to read them. Each one contains "C:\\Users\\<name>\\...", which would
de-anonymise a double-blind artifact submission through a file no human wrote.

  python writeup/judge2026/derelativise_provenance.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# An absolute path on any of the three platforms this could have run on.
ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]|^/home/|^/Users/|^\\\\")


def relativise(value: str) -> str | None:
    """Return the repo-relative tail of an absolute path, or None to leave alone."""
    if not ABSOLUTE.search(value):
        return None
    normalised = value.replace("\\", "/")
    m = re.search(r"(results/.*)$", normalised)
    return m.group(1) if m else None


def main() -> int:
    check_only = "--check" in sys.argv
    files = sorted((REPO / "results").rglob("provenance.json"))
    changed, leaks = [], []

    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        before = dict(data)
        for key, value in data.items():
            if isinstance(value, str):
                rel = relativise(value)
                if rel:
                    data[key] = rel
        if data != before:
            rel_path = p.relative_to(REPO).as_posix()
            changed.append((rel_path, before, data))
            if not check_only:
                p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    # Independent of the rewrite: does any absolute path survive anywhere?
    for p in files:
        text = p.read_text(encoding="utf-8")
        if re.search(r"[A-Za-z]:\\\\|[A-Za-z]:/|/Users/|/home/", text):
            leaks.append(p.relative_to(REPO).as_posix())

    print(f"scanned {len(files)} provenance files")
    for rel_path, before, after in changed:
        key = next(k for k in after if after[k] != before[k])
        print(f"  {rel_path}")
        print(f"     was  {before[key]}")
        print(f"     now  {after[key]}")
    if not changed:
        print("  nothing to rewrite")

    print(f"\nresidual absolute paths: {leaks or 'none'}")
    if check_only and changed:
        print("CHECK FAILED: absolute paths still present")
        return 1
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
