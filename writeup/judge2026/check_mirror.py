"""Simulate the anonymous mirror and fail on anything that would de-anonymise it.

The mirror is the single highest-risk step in a double-blind submission, and it
fails silently: you get a working URL, the repo looks right, and the leak is in
a file nobody opens. This enumerates exactly what a reviewer would be able to
read, so the mirror is verified rather than hoped for.

Two independent defences, because term-substitution alone is fragile:

  1. EXCLUDE  -- paths kept out of the mirror entirely. The MATS application
     materials in writeup/ are not research artifacts; they carry the repo URL
     (which contains the surname) and reveal that the work was prepared for a
     named fellowship. A JUDGe reviewer has no reason to see them.

  2. TERMS    -- strings handed to anonymous.4open.science's anonymisation list
     for the files that DO ship. LICENSE legitimately names the copyright
     holder and PREREGISTRATION.md legitimately names the author; both must
     stay in the real repo and be substituted only in the mirror.

Run before creating the mirror, and again after, against the mirror URL.

  python writeup/judge2026/check_mirror.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# Kept OUT of the mirror. Anything here is unreviewed by the anonymity scan
# because a reviewer will never see it.
EXCLUDE = [
    "writeup/",          # MATS application materials + this checklist
    ".env",
    ".gitignore",
]

# Strings that must not survive into anything a reviewer can read. These are
# also the exact terms to paste into 4open.science's anonymisation field.
TERMS = [
    "Aarav", "aarav", "AARAV",
    "Shah", "shah",
    "aarav7.shah@gmail.com",
    "Aarav500",
    "model-diffing-specificity",
]

# Files where a term is EXPECTED and must be handled by substitution rather
# than deletion, because removing it would damage the real repository.
SUBSTITUTE_OK = {
    "LICENSE": "MIT requires a named copyright holder; without one the licence "
               "is legally weak. Keep the name in the real repo, substitute in "
               "the mirror.",
    "PREREGISTRATION.md": "The author line is part of the pre-registration's "
                          "value as a record. Substitute in the mirror.",
}

BINARY = {".png", ".jpg", ".pdf", ".docx", ".safetensors", ".bin", ".pt", ".gz"}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return out.stdout.split()


def excluded(path: str) -> bool:
    return any(path == e or path.startswith(e) for e in EXCLUDE)


def main() -> int:
    files = tracked_files()
    shipped = [f for f in files if not excluded(f)]
    held = [f for f in files if excluded(f)]

    print(f"tracked {len(files)} files")
    print(f"  mirror ships   {len(shipped)}")
    print(f"  mirror excludes{len(held):>4}   ({', '.join(sorted(EXCLUDE))})")

    term_re = re.compile("|".join(re.escape(t) for t in TERMS))
    needs_substitution: dict[str, list[str]] = {}
    unexpected: dict[str, list[str]] = {}

    for f in shipped:
        p = REPO / f
        if p.suffix.lower() in BINARY or not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits = sorted(set(term_re.findall(text)))
        if not hits:
            continue
        (needs_substitution if Path(f).name in SUBSTITUTE_OK else unexpected)[f] = hits

    print("\nEXPECTED -- handled by the 4open.science term list")
    if not needs_substitution:
        print("  none")
    for f, hits in sorted(needs_substitution.items()):
        print(f"  {f:28s} {hits}")
        print(f"      {SUBSTITUTE_OK[Path(f).name]}")

    print("\nUNEXPECTED -- fix these in the repo, do not rely on substitution")
    if not unexpected:
        print("  none")
    for f, hits in sorted(unexpected.items()):
        print(f"  {f:28s} {hits}")

    # Absolute paths embed a username without ever naming a person, which is how
    # the provenance files leaked. Checked separately from the term list.
    print("\nABSOLUTE LOCAL PATHS (leak a username with no name in them)")
    abs_re = re.compile(r"[A-Za-z]:\\\\Users|[A-Za-z]:/Users|/home/[a-z]|/Users/[a-z]")
    abs_hits = []
    for f in shipped:
        p = REPO / f
        if p.suffix.lower() in BINARY or not p.exists():
            continue
        try:
            if abs_re.search(p.read_text(encoding="utf-8")):
                abs_hits.append(f)
        except (UnicodeDecodeError, OSError):
            continue
    print(f"  {abs_hits or 'none'}")

    print("\nTERMS TO PASTE INTO 4open.science")
    print("  " + ", ".join(TERMS))

    fail = len(unexpected) + len(abs_hits)
    print(f"\n{'PASS' if fail == 0 else 'FAIL: %d file(s) need fixing' % fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
