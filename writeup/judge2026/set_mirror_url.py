"""Set (or clear) the anonymous mirror URL in paper.tex.

Why a script rather than editing the .tex by hand: the single worst outcome for
this submission is pasting the real GitHub URL into a double-blind paper. The
repo is `Aarav500/model-diffing-specificity` -- the surname is in the URL, so
that one paste de-anonymises the submission as surely as a byline would. This
refuses any host that is not anonymous.4open.science, and names the reason.

It rewrites exactly one line -- the \\newcommand{\\mirrorurl}{...} definition --
so it is idempotent and cannot corrupt prose. Re-run it to change the URL, or
pass --clear to remove it.

  python writeup/judge2026/set_mirror_url.py https://anonymous.4open.science/r/abc123
  python writeup/judge2026/set_mirror_url.py --clear
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
TEX = HERE / "paper.tex"

ALLOWED_HOST = "anonymous.4open.science"

# Hosts that would de-anonymise. Listed explicitly so the error can say why,
# rather than just "wrong host".
FORBIDDEN = {
    "github.com": "the repository name contains the author's surname",
    "www.github.com": "the repository name contains the author's surname",
    "gitlab.com": "identifies the account owner",
    "bitbucket.org": "identifies the account owner",
    "drive.google.com": "Google Drive links expose the owning account",
    "dropbox.com": "identifies the account owner",
}

DEFINITION = re.compile(r"^\\newcommand\{\\mirrorurl\}\{.*\}$", re.M)


def validate(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        sys.exit(f"REFUSED: '{url}' is not an http(s) URL.")

    host = parsed.netloc.lower()
    if host in FORBIDDEN:
        sys.exit(
            f"REFUSED: {host} would de-anonymise the submission "
            f"({FORBIDDEN[host]}).\n"
            f"         Create the mirror at https://{ALLOWED_HOST}/ first."
        )
    if host != ALLOWED_HOST:
        sys.exit(
            f"REFUSED: host is '{host}', expected '{ALLOWED_HOST}'.\n"
            f"         If you meant a different anonymising service, add it to\n"
            f"         ALLOWED_HOST in this file deliberately -- do not bypass."
        )

    # A bare host with no repository path is a paste error, not a mirror.
    if parsed.path.strip("/") == "":
        sys.exit(f"REFUSED: '{url}' has no repository path (expected /r/<id>).")

    # LaTeX chokes on unescaped % and # even inside \url.
    for ch in "%#":
        if ch in url:
            sys.exit(f"REFUSED: URL contains '{ch}', which LaTeX cannot take raw.")

    return url


def main() -> int:
    args = [a for a in sys.argv[1:] if a.strip()]
    if not args:
        sys.exit(__doc__.strip().splitlines()[-3].strip())

    src = TEX.read_text(encoding="utf-8")
    if not DEFINITION.search(src):
        sys.exit(r"Could not find the \newcommand{\mirrorurl}{...} line in paper.tex.")

    if args[0] == "--clear":
        url, msg = "", "cleared -- \\mirrornote now expands to nothing"
    else:
        url = validate(args[0])
        msg = f"set to {url}"

    out = DEFINITION.sub(r"\\newcommand{\\mirrorurl}{" + url + "}", src, count=1)
    if out != src:
        TEX.write_text(out, encoding="utf-8")
    print(f"mirror URL {msg}")

    print("\nrebuilding...")
    return rebuild()


def rebuild(max_passes: int = 5) -> int:
    """Run the build without shelling out to bash.

    Not a duplicate of build.sh by preference. Invoking "bash" from Python on
    Windows resolves to WSL's bash, which has no LaTeX toolchain and fails with
    an execvpe error that reads like a LaTeX problem. Driving pdflatex directly
    removes the shell from the path entirely and works the same everywhere.
    """
    log = HERE / "build.log"

    r = subprocess.run([sys.executable, "figure_ladder.py"], cwd=HERE,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("  FIGURE FAILED\n" + (r.stderr or r.stdout)[-600:])
        return r.returncode

    # Iterate to a fixed point: \ref resolves from the previous run's .aux, so
    # adding a footnote can leave pass 2 still unstable.
    unstable = re.compile(r"Rerun to get|Label\(s\) may have changed|undefined references")
    for i in range(1, max_passes + 1):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                            "-halt-on-error", "paper.tex"],
                           cwd=HERE, capture_output=True, text=True)
        log.write_text(r.stdout, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            errs = [l for l in r.stdout.splitlines() if l.startswith("!")]
            print(f"  LATEX FAILED on pass {i}: {errs[:3] or 'see build.log'}")
            return r.returncode
        if not unstable.search(r.stdout):
            print(f"  latex stable after {i} pass(es)")
            break
    else:
        print(f"  latex still unstable after {max_passes} passes")

    pages = re.search(r"Output written on paper\.pdf \((\d+) pages?", r.stdout)
    print(f"  pages: {pages.group(1) if pages else 'UNKNOWN'}")

    g = subprocess.run([sys.executable, "check_paper.py"], cwd=HERE,
                       capture_output=True, text=True)
    keep = re.compile(r"mirror URL|reaches the rendered|PASS|FAIL|-- FIX")
    print("\n".join("  " + l.strip() for l in g.stdout.splitlines() if keep.search(l)))
    return g.returncode


if __name__ == "__main__":
    sys.exit(main())
