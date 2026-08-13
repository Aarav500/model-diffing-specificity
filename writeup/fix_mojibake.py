"""Repair UTF-8-read-as-cp1252 damage in a source file, and FAIL if any remains.

Why the repair is generic and not a hand-written lookup table
------------------------------------------------------------
The previous version could only fix sequences someone had remembered to list.
U+2192 (an arrow) encodes to E2 86 92, and cp1252 reads byte 86 as U+2020 --
outside the "\\u00e2\\u20ac..." family that every other entry in that table
shared. So it did not look like its neighbours, was never added, and survived
three repair passes into two figure captions and a headline takeaway.

The fix is to stop enumerating. Mojibake is exactly "these bytes were UTF-8 and
got decoded as cp1252", which is mechanically invertible: re-encode to cp1252,
decode as UTF-8. If both succeed, the text WAS mojibake and the result is the
original. If either raises, it was not, and the text is left untouched. That
covers every sequence, including ones nobody has hit yet.

A whole-file round trip fails here because the file is MIXED -- some edits wrote
correct UTF-8 and a PowerShell write corrupted the rest -- so the inversion is
applied per maximal non-ASCII run.

Why this file is pure ASCII
---------------------------
A tool that repairs encoding damage must not be corruptible by it, and a table
of hand-typed damaged characters is unreviewable (they render differently in
every editor) and easy to get subtly wrong. Nothing here is hand-typed: the
fallback table is DERIVED by applying the corruption to characters we care
about, so a wrong entry is not possible.

Exit status
-----------
Non-zero if suspicious sequences survive, so this can be used as a gate.

  python writeup/fix_mojibake.py <file>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A maximal run of non-ASCII characters -- the unit of repair. ASCII text
# between runs is untouched, so "falls 0.55 <moji> 0.05" isolates cleanly.
RUN = re.compile(r"[^\x00-\x7f]+")

# The signature of cp1252-misread UTF-8: a leading a-circumflex / A-tilde /
# A-circumflex followed by another non-ASCII char. Checked AFTER repair and
# independently of how the repair works, so anything unfixable fails loudly.
SIGNATURE = re.compile("[âÃÂ][^\x00-\x7f]")

# Characters this project actually uses that would be damaged by a cp1252
# misread. Arrows first -- the ones that got away.
AT_RISK = (
    "→←↑↓"          # arrows
    "—–"                      # em dash, en dash
    "“”‘’"          # curly quotes
    "…•"                      # ellipsis, bullet
    "≥≤−×±"    # >=, <=, minus, times, plus-minus
    "§°éí"          # section, degree, e-acute, i-acute
    "ρκασμ"    # rho, kappa, alpha, sigma, mu
)


def corrupt(ch: str) -> str | None:
    """Apply the damage: UTF-8 bytes misread as cp1252. None if not expressible."""
    try:
        return ch.encode("utf-8").decode("cp1252")
    except UnicodeDecodeError:
        # Bytes 81/8D/8F/90/9D are undefined in cp1252, so this damage cannot
        # be represented as text at all -- it could never appear in the file.
        return None


def invert(run: str) -> str | None:
    """Undo one cp1252-misread of UTF-8, or None if `run` was not that."""
    try:
        return run.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None


# Fallback for runs the generic pass cannot take whole -- e.g. correct UTF-8
# sitting flush against damaged bytes with no ASCII between them, which makes
# the combined run invalid as a unit. Longest first so a shorter pattern cannot
# eat the prefix of a longer one.
KNOWN = sorted(
    ((bad, ch) for ch in AT_RISK if (bad := corrupt(ch)) is not None),
    key=lambda kv: -len(kv[0]),
)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[-1])
        return 2

    path = Path(sys.argv[1])
    src = path.read_text(encoding="utf-8")

    if src[:1] == "﻿":
        print("stripped UTF-8 BOM")
        src = src[1:]

    repaired: list[tuple[str, str]] = []

    def fix_run(m: re.Match[str]) -> str:
        run = m.group(0)
        out = invert(run)
        if out is not None and out != run:
            repaired.append((run, out))
            return out
        return run

    out = RUN.sub(fix_run, src)

    for bad, good in KNOWN:
        if bad in out:
            repaired.append((bad, good))
            out = out.replace(bad, good)

    if not repaired:
        print("no mojibake found")
    for bad, good in repaired:
        print(f"  {bad!a} -> {good!a}   ({good})")

    residual = SIGNATURE.findall(out)
    if residual:
        shown = sorted(set(ascii(r) for r in residual))
        print(f"\nFAIL: {len(residual)} suspicious sequence(s) survive: {shown}")
        print("Not writing. Inspect by hand.")
        return 1

    if out == src:
        print(f"clean; {path} unchanged")
        return 0

    path.write_text(out, encoding="utf-8")
    print(f"clean; wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
