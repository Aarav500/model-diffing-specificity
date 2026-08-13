"""Audit the review page for the classic unreadable-artifact bug.

Checks that no color literal is declared inside a component rule -- every colour
must come from a token defined in :root and redefined in both theme blocks, or
the page renders one theme's text on the other theme's ground.
"""

import re
from pathlib import Path

h = Path(__file__).resolve().parent.joinpath("review.html").read_text(encoding="utf-8")
css = h[h.find("<style>"):h.find("</style>")]

# Strip token blocks; whatever colour literals remain live in component rules.
stripped = re.sub(r":root[^{]*\{[^}]*\}", "", css)
stripped = re.sub(r"@media[^{]*\{\s*:root[^{]*\{[^}]*\}\s*\}", "", stripped)
lits = sorted(set(re.findall(r"#[0-9A-Fa-f]{3,8}", stripped)))

print("colour literals in component rules:", lits or "none")
print("  (mark's #FDE68A is intentional - a highlight reads the same on both grounds)")
print()
print("token blocks   : :root x%d | prefers-color-scheme x%d | [data-theme=dark] x%d"
      % (css.count(":root{"), css.count("prefers-color-scheme"),
         css.count('[data-theme="dark"]')))
print("body ground    :", "background:var(--paper)" in css)
print("focus visible  :", "focus-visible" in css)
print("reduced motion :", "prefers-reduced-motion" in css)
print("wide overflow  :", ".tw{overflow-x:auto" in css)
print()
print("quoted blocks  :", h.count('class="quoted"'))
print("arm heads      :", h.count('class="armhead"'))
print("figures        :", h.count("<figure>"))
print("size           : %.0f KB" % (len(h) / 1024))
