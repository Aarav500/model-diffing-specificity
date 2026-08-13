"""Repair UTF-8-read-as-cp1252 damage in a source file.

A whole-file reverse (encode cp1252 / decode utf-8) fails here because the file
is MIXED: some edits wrote correct UTF-8 and a PowerShell write corrupted the
rest. So patch the specific damaged sequences instead, longest-first so shorter
patterns cannot eat the prefix of a longer one.
"""

import sys
from pathlib import Path

# Longest first. Order matters: 'â€"' must be tried before 'â€'.
REPAIRS = [
    ("â€”", "—"), ("â€“", "–"), ("â€œ", "“"), ("â€\x9d", "”"),
    ("â€™", "’"), ("â€˜", "‘"), ("â€¦", "…"), ("â€¢", "•"),
    ("â‰¥", "≥"), ("â‰¤", "≤"), ("âˆ’", "−"), ("Ã—", "×"),
    ("Ï\x81", "ρ"), ("Î±", "α"), ("Îº", "κ"), ("Â§", "§"),
    ("Â ", " "), ("Ã©", "é"),
]


def main():
    p = Path(sys.argv[1])
    src = p.read_text(encoding="utf-8")

    if src and src[0] == "﻿":
        print("stripped UTF-8 BOM")
        src = src[1:]

    out = src
    hits = []
    for bad, good in REPAIRS:
        if bad in out:
            hits.append((bad, good, out.count(bad)))
            out = out.replace(bad, good)

    if not hits:
        print("no known mojibake sequences found")
    for bad, good, n in hits:
        print(f"  {n:>3} x {bad!r} -> {good!r}")

    # Anything left in the mojibake danger zone is unpatched damage; report it
    # rather than write a file that silently still contains it.
    leftover = sorted({c for c in out if "" <= c <= "¿"} - {" ", "°"})
    print("residual suspicious chars:", leftover or "none")

    p.write_text(out, encoding="utf-8")
    for probe in ["— end of executive summary —", "grade ≥ 2", "ρ = −0.94",
                  "exactly zero signal by construction"]:
        print(f"  {probe in out}  {probe}")
    print("wrote", p)


if __name__ == "__main__":
    main()
