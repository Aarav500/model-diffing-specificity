# JUDGe 2026 — pre-submission checklist

Deadline **2026-08-29, 11:59 PM AoE**. Portal: OpenReview. Double-blind, non-archival.
Today is 2026-08-13, so there are 16 days.

Build and gate everything with:

```bash
bash writeup/judge2026/build.sh
```

That runs `pdflatex` **twice** (a single pass shipped a PDF reading "Figure ??"), regenerates
the figure from the study artifacts, and then runs `check_paper.py`, which fails on a
de-anonymising string, a banned overclaim, a missing hedge, or a body outside 1100–1400 words.

---

## ⚠️ THE ONE THAT WILL SINK IT — anonymous mirror

**The paper currently contains no repository URL at all.** I left it out rather than write a
placeholder that could survive into a submitted PDF. Before you add a link, note the trap:

> The repo is `github.com/Aarav500/model-diffing-specificity`. **Your surname is in the URL.**
> Pasting it into a double-blind submission de-anonymises you as surely as a byline.

### I could not create this for you — and why

Anonymous GitHub requires **signing in with your GitHub account (OAuth)**. Authenticating as
you on a third-party service is something I will not do; the authorisation has to be granted
by you, in your own browser. Everything up to that click is done and verified below.

The service only ever *reads* your repository — it never pushes, modifies, or deletes.

### What is already done

`check_mirror.py` simulates the mirror and reports exactly what a reviewer could read.
Current result: **PASS**, with precisely two files naming you, both legitimately:

```bash
python writeup/judge2026/check_mirror.py
```

| File | Why it names you | Handling |
|---|---|---|
| `LICENSE` | MIT needs a named copyright holder; without one the licence is legally weak | term substitution |
| `PREREGISTRATION.md` | the author line is part of the record's value | term substitution |

It also caught a leak that contains **no name at all**: seven `results/artifacts/*/provenance.json`
files embedded `C:\Users\aarav\...`. Machine-generated, so nobody opens them. Now rewritten to
repo-relative paths, which name the same referent and are reproducible elsewhere.

### Steps (verified against the service, 2026-08-13)

1. Go to <https://anonymous.4open.science/> and **sign in with GitHub**.
2. Point it at `Aarav500/model-diffing-specificity`, branch `main`.
3. Paste the anonymisation terms — the field takes **one regex per line**:

   ```
   Aarav
   aarav
   AARAV
   Shah
   shah
   aarav7.shah@gmail.com
   Aarav500
   model-diffing-specificity
   ```

   The owner/organisation name is replaced automatically, but **file contents are only
   redacted for terms you list** — which is why `LICENSE` and `PREREGISTRATION.md` above
   must be in the list.
4. **Exclude `writeup/`.** It holds the MATS application materials, which carry the repo URL
   and reveal the work was prepared for a named fellowship. A JUDGe reviewer has no reason to
   see them, and no term list makes that context anonymous.
5. Set the expiry past the workshop: **2026-12-31** (event is Dec 12–13).
6. Open the resulting URL and spot-check `LICENSE` and `PREREGISTRATION.md` render redacted.
7. **Paste the URL into one command.** Do not hand-edit `paper.tex`:

   ```bash
   python writeup/judge2026/set_mirror_url.py https://anonymous.4open.science/r/XXXX
   ```

   It validates the URL, inserts the §2 footnote, rebuilds, and re-runs every gate.
   Re-run it to change the URL; `--clear` removes it.

   **It refuses `github.com` by name**, because pasting the real repo URL is the single
   worst outcome here and the surname is in it. It also refuses a bare host with no
   repository path, a non-http scheme, and any URL containing `%` or `#` (which LaTeX
   cannot take raw). Tested against all of these.

   While unset, `\mirrornote` expands to nothing — so the paper compiles and is correctly
   shaped with or without the mirror, and no placeholder can ever ship.

## The other five blockers

| # | Item | Status |
|---|---|---|
| 1 | Decide yes/no | **My recommendation: submit.** Reasoning below. |
| 2 | Anonymous mirror | **Prepared and verified; the OAuth click is yours.** Repo now passes `check_mirror.py`. See above. |
| 3 | Add a LICENSE | **DONE.** MIT at the repo root, `Copyright (c) 2026 Aarav Shah`. GitHub will now detect it, so the artifact is citable and usable. |
| 4 | OpenReview account | **Blocked on you.** Only submission route. Accounts can take time to be activated — do this first, not last. |
| 5 | Confirm sole authorship | You confirmed sole authorship earlier for the MATS document. The paper says "Anonymous submission" and adds no acknowledgements, so nothing changes unless that is no longer true. |
| 6 | Ladder numbers in plottable form | **Done — no fallback needed.** See below. |

### #6 is fully resolved — all six rungs exist

You flagged the risk that only the endpoints (0.55 and 0.05) existed and the figure would
degrade to a two-point comparison. It does not. Verified from `results/` in the repo:

| Rung | n | Assertion | Accuracy (grade ≥ 4) |
|---|---|---|---|
| 1 : 0   | 20 | 1.00 (20/20) | 0.55 (11/20) |
| 1 : 0.1 | 20 | 1.00 (20/20) | 0.35 (7/20) |
| 1 : 0.3 | 20 | 1.00 (20/20) | **0.50 (10/20)** |
| 1 : 0.5 | 20 | 1.00 (20/20) | 0.30 (6/20) |
| 1 : 1.0 | 20 | 1.00 (20/20) | 0.10 (2/20) |
| 1 : 2.0 | 20 | 1.00 (20/20) | 0.05 (1/20) |

**The decline is not monotone — 1:0.3 rebounds to 0.50.** The figure annotates this, the
caption states it, and the limitations paragraph repeats it. Hiding it would have been the
easy move and exactly the failure this paper is about; a reviewer plotting the numbers would
have found it in a minute.

`figure_ladder.py` reads these from the artifacts rather than hard-coding them, so the figure
cannot drift from the data.

### Exact plotting spec (as requested)

- **Type:** dual line series over six ordinal x-positions, with a shaded band between them.
- **x-axis:** the six rungs, **equally spaced**. Not linear (would crush the first four
  against the origin) and not log (undefined at the 1:0 rung). Equal spacing asserts nothing
  about the spacing of the ratios. Label `Dilution (finetuning : pretraining mix)`.
- **y-axis:** `Rate`, limits −0.04 to 1.08, ticks at 0 / 0.25 / 0.5 / 0.75 / 1.0.
- **Series A — assertion rate:** solid, `#B42318`, filled circles, lw 1.9. Flat at 1.00.
- **Series B — accuracy (grade ≥ 4):** dashed, `#1D4ED8`, open squares (white fill), lw 1.9.
- **Band:** `fill_between(accuracy, assertion)`, `#94A3B8` at alpha 0.28, **labelled in the
  legend** as "Gap: invisible to a sensitivity-only evaluation". The gap is the finding, so
  it is a labelled element, not incidental whitespace.
- **Error bars:** Clopper–Pearson exact 95%, n = 20 per rung, capsize 2.5.
- **Annotation:** "decline is not monotone" → the 1:0.3 marker, kept clear of the 1.00 line.
- **Legend:** below the axes, 3 columns, frameless. Inside the panel it sat on top of the
  accuracy line — the one series the figure exists to show.
- **Size:** 6.2 × 1.95 in at 300 dpi, placed at `0.80\linewidth`. Vector PDF for LaTeX.

## Timing — my recommendation, on purpose

**Submit.** JUDGe closes 2026-08-29; MATS (Neel Nanda stream) closes 2026-09-04. Six days
apart, and the paper is a compression of work that already exists, so the marginal cost is
mostly the anonymisation chores above rather than new research.

Three things make it clearly positive:

- **Non-archival means it burns nothing.** The work stays eligible for a real venue later.
- **The Junior Spotlight assigns a senior researcher to give feedback before the event.** For
  a first workshop paper that is the actual prize, above the oral.
- **It answers the "was this written for an application?" objection** by showing the work went
  somewhere independent of the application.

The one real consideration, stated plainly rather than waved away: **Nanda is a co-author of
the ADL paper this audits, and reads the MATS application.** That cuts in your favour on the
evidence available — the paper reproduces ADL's positive result (20/20), explicitly declines
to claim the method is broken, and says its own grades are not comparable to ADL's 91%. An
audit that is careful about the limits of its own critique is a better signal than one that
overreaches. The failure mode to avoid is not *submitting*; it is letting the two documents
drift into saying different things. They currently agree.

**Sequence:** OpenReview account (#4) and LICENSE (#3) today — both are slow-and-external.
Mirror (#2) once the LICENSE is in. Paper is already built and gated.

## Anonymity is machine-checked, not eyeballed

`check_paper.py` scans the **rendered** text (LaTeX comments stripped, since reviewers see the
PDF) for `Aarav`, `aarav`, `Shah`, `github.com/Aarav500`, `model-diffing-specificity`, and
`\usepackage[final]` — the NeurIPS option that prints author names. It also catches the
malformed-length bug that silently shrank the figure to a thumbnail during drafting
(`0.74\linewidth` → `0.74inewidth`, which LaTeX reads as a valid 0.74 inches and compiles
without complaint).

Current status: **PASS**, 2 pages plus references, abstract 121 words, body 1111 words.

## Still to fill before submitting

- [ ] Anonymous mirror URL added to `paper.tex` (§2 footnote)
- [ ] ADL citation: **author initials and exact title are not verified.** The bibliography
      currently lists surnames only (Minder, Dumas, Slocum, Casademunt, Holmes, West, Nanda)
      plus `arXiv:2510.13900` and ICLR 2026, which are verified. Fill the initials and the
      full title from the arXiv page — do not guess them.
- [ ] Confirm the venue wants US Letter (the geometry here is Letter, not A4)
- [ ] If using the official `neurips_2026.sty`, re-run `build.sh` and re-check the page count;
      the current geometry only approximates it
