// Builds the MATS write-up, matching the structure of MATS_Nanda_Application_RHOB.docx.
// Run:  node writeup/build_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, LevelFormat,
  ImageRun, ExternalHyperlink, PageBreak,
} = require("docx");

const REPO_URL = "https://github.com/Aarav500/model-diffing-specificity";

// Both figures render at 9 x 5.4in / 200dpi. Usable page width is 6.5in, so
// scale to 620px wide and keep the aspect ratio exactly.
const figure = (file) => new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync(path.join(__dirname, "..", "results", file)),
    transformation: { width: 620, height: 372 },
  })],
});

const link = (url, text) => new ExternalHyperlink({
  link: url,
  children: [new TextRun({ text: text || url, style: "Hyperlink" })],
});

// Pull the randomly-sampled reports straight out of the artifact sample_outputs.py
// wrote, so the document cannot drift from the file whose sampling seed is fixed
// in source. Bodies are truncated for length; the full text is in the repo.
function sampledExamples(maxChars = 620) {
  // Normalise CRLF first: the file is written on Windows, so a bare \n in the
  // fence regexes below silently matches nothing and the section comes out empty.
  const md = fs.readFileSync(
    path.join(__dirname, "..", "results", "D5_sampled_outputs.md"), "utf8"
  ).replace(/\r\n/g, "\n");
  const out = [];
  const blocks = md.split(/^## Arm /m).slice(1);
  for (const blk of blocks) {
    const arm = (blk.match(/^`([^`]+)`/) || [, "?"])[1];
    const grade = (blk.match(/\*\*Blind grade:\*\*\s*(.+)/) || [, ""])[1].trim();
    const body = (blk.match(/```\n([\s\S]*?)\n```/) || [, ""])[1].trim();
    if (!body) continue;
    const clipped = body.length > maxChars
      ? body.slice(0, maxChars).replace(/\s+\S*$/, "") + " […]"
      : body;
    out.push(new Paragraph({
      spacing: { before: 160, after: 40 },
      children: [b(`Arm ${arm}`), t("   "),
                 new TextRun({ text: grade, size: 18, color: "666666" })],
    }));
    for (const line of clipped.split("\n")) {
      out.push(new Paragraph({
        spacing: { after: 0 },
        indent: { left: 260 },
        children: [new TextRun({ text: line, size: 18 })],
      }));
    }
  }
  return out;
}

// The deviations count is DERIVED from PREREGISTRATION.md, never typed. It was
// hand-written in two places and drifted to two different wrong numbers ("nine"
// in the front matter, "seven" in the repo section) against an actual ten. A
// document whose credibility claim is the completeness of that log cannot
// contradict the log about its own size.
function deviationCount() {
  const md = fs.readFileSync(path.join(__dirname, "..", "PREREGISTRATION.md"), "utf8")
    .replace(/\r\n/g, "\n");
  const sec = md.split(/^#+ .*Deviations log.*$/m)[1];
  if (!sec) throw new Error("deviations log section not found in PREREGISTRATION.md");
  const body = sec.split(/^#+ /m)[0];
  const rows = body.split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("|"))
    .filter((l) => !/^\|[\s|:-]+\|$/.test(l))   // separator
    .filter((l) => !/^\|\s*Date\s*\|/.test(l)); // header
  if (rows.length === 0) throw new Error("deviations log parsed to zero rows");
  return rows.length;
}

const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
               "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen"];
const NDEV = deviationCount();
const NDEV_WORD = WORDS[NDEV] || String(NDEV);
const NDEV_CAP = NDEV_WORD[0].toUpperCase() + NDEV_WORD.slice(1);

const W = 9360; // usable width for US Letter with 1.44" total margins, in DXA

const p = (text, opts = {}) => new Paragraph({ ...opts, children: [new TextRun(text)] });
const runs = (children, opts = {}) => new Paragraph({ ...opts, children });
const b = (x) => new TextRun({ text: x, bold: true });
const i = (x) => new TextRun({ text: x, italics: true });
const t = (x) => new TextRun(x);
const mono = (x) => new TextRun({ text: x, font: "Consolas", size: 19 });
const fill = (x) => new TextRun({ text: x, bold: true, highlight: "yellow" });

const bullet = (children) =>
  new Paragraph({ numbering: { reference: "bullets", level: 0 }, children });

const h1 = (x) => new Paragraph({ text: x, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 140 } });
const h2 = (x) => new Paragraph({ text: x, heading: HeadingLevel.HEADING_2, spacing: { before: 260, after: 110 } });

const metaRow = (k, cells) =>
  new TableRow({
    children: [
      new TableCell({
        width: { size: 2000, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
        children: [runs([b(k)])],
      }),
      new TableCell({ width: { size: W - 2000, type: WidthType.DXA }, children: cells }),
    ],
  });

// Ladder table: ratio / assert / grade>=2 / grade>=4
const ladderRow = (cells, header = false) =>
  new TableRow({
    children: cells.map((c, n) => new TableCell({
      width: { size: n === 0 ? 2400 : (W - 2400) / 3, type: WidthType.DXA },
      shading: header ? { type: ShadingType.CLEAR, fill: "F2F2F2" } : undefined,
      children: [runs([header ? b(c) : t(c)])],
    })),
  });

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 460, hanging: 260 } } },
      }],
    }],
  },
  styles: { default: { document: { run: { font: "Calibri", size: 22 } } } },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children: [
      runs([new TextRun({ text: "What a model-diffing agent says about a model with nothing to find", bold: true, size: 30 })]),
      runs([new TextRun({ text: "MATS Winter 2027 application — Neel Nanda stream", size: 22, color: "555555" })], { spacing: { after: 240 } }),

      new Table({
        columnWidths: [2000, W - 2000],
        width: { size: W, type: WidthType.DXA },
        rows: [
          metaRow("Route", [p("New research done for this application. Sprint project.")]),
          metaRow("Authorship", [p("Sole author. All code, experiments, literature verification and this document.")]),
          metaRow("Time spent", [p("18 hours.")]),
          metaRow("Code", [runs([link(REPO_URL), t("  — MIT. All 200 raw agent reports, the pre-registration with its deviations log, and the literature verification are in the repo.")])]),
          metaRow("Scale", [p("200 blind agent runs. Agent gpt-5-2025-08-07 (ADL's own, pinned snapshot); grader gpt-5-mini.")]),
          metaRow("Pre-registration", [runs([t("Rubric and analysis plan committed at "), mono("34e0807"), t(", "), mono("2026-08-12 19:57:24 -0500"), t(`, before any results existed. ${NDEV_CAP} deviations logged in-file, not amended away — including abandoning the pre-registered headline false-positive rate.`)])]),
        ],
      }),

      h1("Executive summary"),

      h2("The problem"),
      runs([
        t("Activation Difference Lens (Minder et al., arXiv:2510.13900) reports a white-box diffing agent naming the finetuning objective for 91% of organisms at grade ≥ 2, against 39% black-box — a sensitivity number. The absent arm is field-wide: Delta-Crosscoder's only null is two identical copies of one model, "),
        b("exactly zero signal by construction"),
        t("; AuditBench's 56 organisms are all positives; neither Model Organisms Are Leaky nor Cross-Architecture Diffing reports a neutral null. Nulls do exist — Chughtai, Engels & Nanda (June 2026) on identical pairs, Egler et al. at 56.2%/1% FPR — but each is zero-delta or black-box. I set out to measure the white-box case none covers, reproduced ADL's control, then "),
        i("failed to measure a false-positive rate"),
        t(", because every null I built contained a real signal. What replaced it is sharper: the agent's "),
        b("confidence is decoupled from its evidence"),
        t("."),
      ]),

      h2("Takeaways"),
      bullet([b("The method reproduces. "), t("Arm P: 20/20 on "), mono("cake_bake"), t(" — one of the 33 organisms behind their 91%. The failures below are not a broken reimplementation.")]),
      bullet([b("There may be no such thing as a no-objective finetune. "), t("Three nulls, three contaminations: FineWeb is itself a register; two seeds on identical data differ along the domain axis; instruction-tuning is an objective.")]),
      // Both halves of this bullet are restated in full, with their statistics,
      // by Experiments 2 and 3 immediately below. It states the claim and the
      // headline numbers; the evidence lives there.
      bullet([b("Confidence is decoupled from evidence, two ways. "), t("Framing manufactures answers: 9/9 assertions against 2/10 on "), i("identical evidence"), t(". Down a dilution ladder, assertion holds at 1.00 while accuracy falls 0.55 → 0.05. Both below.")]),

      h2("Experiment 1: it reproduces"),
      runs([t("200 blind runs — neither agent nor grader learns the arm, and the grader never sees ground truth. Arm P returns "), i("“professional culinary/baking assistant”"), t(" on all 20 runs, under both framings, with perfect cross-seed agreement.")]),

      h2("Experiment 2: framing, not activations"),
      runs([t("N0 ("), mono("pt"), t(" vs "), mono("it"), t(") is the only arm with no "), i("narrow"), t(" objective. Presuppositional: 9/9 assert. Neutral, same evidence: 2/10. "), b("p = 0.0007."), t(" The presup answers contradict each other across seeds, quoted overleaf. Cross-seed consistency: 0.67 here, 1.00 wherever a real signal exists — a detector needing no labels.")]),

      h2("Experiment 3: the dilution ladder"),
      runs([t("Six released "), mono("mix1-*"), t(" rungs; "), mono("agents.sh"), t(" runs only two, so every lower rung is un-run upstream.")]),
      new Table({
        columnWidths: [2400, (W - 2400) / 3, (W - 2400) / 3, (W - 2400) / 3],
        width: { size: W, type: WidthType.DXA },
        rows: [
          ladderRow(["Mix ratio", "Asserts", "Right domain (≥2)", "Specifically right (≥4)"], true),
          // All six released rungs. An earlier draft showed four, which made the
          // decline look monotone; 1:0.3 rebounds and 1:0.1 is not 1.00 at >=2.
          ladderRow(["1 : 0", "1.00", "1.00", "0.55"]),
          ladderRow(["1 : 0.1", "1.00", "0.95", "0.35"]),
          ladderRow(["1 : 0.3", "1.00", "1.00", "0.50"]),
          ladderRow(["1 : 0.5", "1.00", "1.00", "0.30"]),
          ladderRow(["1 : 1.0", "1.00", "1.00", "0.10"]),
          ladderRow(["1 : 2.0", "1.00", "1.00", "0.05"]),
        ],
      }),
      runs([b("Assertion is flat at 1.00 on all 120 runs while specific accuracy falls elevenfold"), t(" — unevenly: 1:0.3 rebounds. My pre-registered ladder test (ASSERT on dilution, §8) is "), b("undefined here"), t(" — the outcome is constant, so there is no variance to model. That is this project's own failure mode, arriving in my analysis plan. The decline is measured on grade ≥ 4, "), i("exploratory"), t(" (rank-based ρ = −0.94, p = 0.005).")]),

      h2("Limitations"),
      bullet([t("An objective-free but nonzero-delta null is unsolved — the next problem.")]),
      // (word budget is tight; this section is the deliberate donor for the
      // literature sentences the reviewer asked for in "The problem")
      bullet([b("My correctness grades are not comparable to ADL's 91%"), t(": I reconstructed the rubric, theirs grades key-fact recovery. My ≥ 2 sits at 1.00 where they report failure because the binary hides a decline above it — not a refutation.")]),
      bullet([t("n = 10 per cell; 9/9 has a 95% lower bound of 0.66. One model family, one organism, one agent. κ = 1.000 (16/16), but only one case tested the grader. My ADL is a reimplementation.")]),

      h2("Relevance to your stream"),
      runs([t("My previous project audited my own benchmark and found seven claims no observation could have contradicted. Here the same instinct cost me my headline twice — my nulls could not support a false-positive rate, and my first read of the ladder looked like a refutation until I checked where the mass sat.")], { spacing: { after: 40 } }),
      p("— end of executive summary —", { alignment: AlignmentType.CENTER, spacing: { before: 200, after: 200 } }),

      figure("figure1_detection_vs_fpr.png"),
      runs([b("Figure 1. "), t("Assertion rate by arm and prompt framing, Clopper–Pearson 95% intervals. Three arms sit at 1.00 because the agent was "), i("right"), t(". The fourth — the only one with no narrow objective — moves 1.00 → 0.20 on identical evidence when the prompt stops presupposing an answer.")],
           { spacing: { after: 240 } }),

      figure("figure2_dilution_curve.png"),
      runs([b("Figure 2. "), t("Six released dilution rungs, 120 runs. Assertion is flat at 1.00 while grade ≥ 4 accuracy falls 0.55 → 0.05. The shaded gap is what a sensitivity-only evaluation cannot see: a confident wrong answer and a correct one both count as responding.")],
           { spacing: { after: 240 } }),

      h1("The contradiction, in full"),
      runs([t("Arm N0, presuppositional framing, ten independent seeds on byte-identical evidence:")]),
      runs([t("The blind judge splits the nine assertions into two mutually incompatible groups (six and three). Quoting across that split — these two cannot both be true of the same model:")]),
      bullet([mono("s0"), t(" instruction-tuned into a helpful, "), b("safety-aware"), t(" assistant")]),
      bullet([mono("s7"), t(" "), b("uncensored"), t(", sensational/tabloid-style generator (clickbait/gossip/NSFW)")]),
      runs([t("Within the larger group the readings are compatible with each other — “content-moderation classifier”, “keyword extractor”, “summarisation” — so this is not nine mutually exclusive answers. It is one clean contradiction, which is all that is needed: at least one of the nine is wrong, and no ground truth is required to know it. Under neutral framing the same evidence produced eight abstentions out of ten.")]),


      h1("One more result, scoped carefully"),
      runs([b("Within the mix1 family, difference magnitude is anti-correlated with detectability."), t(" Mean diff norm broadly rises down the ladder — 244 (1:0), 163, 207, 254, 358 (1:1), "), b("474 (1:2)"), t(" — while recoverability collapses (Spearman ρ = −0.77, p = 0.07, "), i("exploratory"), t("; note the sequence dips at the first rung rather than rising monotonically). More mixed-in pretraining data means a bigger weight change, spread across generic web text rather than concentrated on the objective.")]),
      runs([b("This does not generalise across arms, and my own data refutes the stronger version."), t(" Arm P has a mean norm of 747 with the best accuracy in the study; N0 has 7756 and no narrow objective at all. So “large delta, worth auditing” is a bad triage heuristic "), i("within a matched family"), t(", and simply uninformative between families. I state the narrow claim because the wide one is the more quotable and is false.")]),

      h1("What is in the repository"),
      bullet([mono("PREREGISTRATION.md"), t(` — rubric, blinding protocol, analysis plan, power limits, and a deviations log with ${NDEV_WORD} entries, each recording whether it was made before or after seeing the affected data.`)]),
      bullet([mono("LITERATURE_VERIFICATION.md"), t(" — five papers checked against primary text. Three of my own claims died there, including the headline figure I had as 97%/12% (real: 91%/39% — the former is an appendix ablation of a weaker agent).")]),
      bullet([mono("FINDINGS.md"), t(", "), mono("results/ARM_NOTES.md"), t(" — results, and why each null failed differently.")]),
      bullet([mono("src/adl_core.py"), t(" — the ADL signal reimplemented in raw HuggingFace hooks: caching, logit lens, Patchscope, steering, directional ablation. No TransformerLens.")]),
      bullet([t("Blinding is enforced, not documented: a scrub raises "), mono("BlindingViolation"), t(" if an identifier would reach the agent, and the run-ID→arm map is gitignored until analysis is locked. "), mono("src/analyze.py"), t(" exits rather than emit placeholder numbers.")]),

      h1("What I specifically contributed"),
      p("Sole author. No other person contributed to any part of this project. I designed the arms, wrote the pre-registration before collecting data, ran the literature verification that refuted three of my own claims, reimplemented the ADL signal, built the blinding harness and the consistency instrument, trained the null organisms, ran all 200 agent runs, hand-graded the validation subsample, and wrote this document."),

      // Sampled outputs are LAST, behind a page break, so the main body reads as
      // a self-contained document and the page budget is spent on argument.
      new Paragraph({ children: [new PageBreak()] }),
      h1("Appendix — randomly sampled raw outputs"),
      runs([t("Neel asks for these explicitly. Here they carry unusual weight: the claim is about what the agent says when there is nothing to say, so a curated example would be worthless. One per arm, uniform within stratum, seed hard-coded in "), mono("src/sample_outputs.py"), t(" so re-rolling the draw would show as a diff. Bodies truncated for length; full text for all 200 runs is in the repo.")]),
      ...sampledExamples(),

      // The "Before you send this" checklist lived here. Every item was
      // verified and it was removed before submission -- it was scaffolding for
      // the author, not content for the reader. Verification is in
      // writeup/audit_discipline.py, which still runs against the built file.
    ],
  }],
});

const out = path.join(__dirname, "MATS_Nanda_Application_ModelDiffingFPR.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log("wrote " + out);
});
