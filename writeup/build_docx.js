// Builds the MATS write-up, matching the structure of MATS_Nanda_Application_RHOB.docx.
// Run:  node writeup/build_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, LevelFormat,
  ImageRun, ExternalHyperlink,
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
          metaRow("Pre-registration", [runs([t("Rubric and analysis plan committed at "), mono("34e0807"), t(", "), mono("2026-08-12 19:57:24 -0500"), t(", before any results existed. Seven deviations logged in-file, not amended away.")])]),
        ],
      }),

      h1("Executive summary"),

      h2("The problem"),
      runs([
        t("Activation Difference Lens (Minder et al., arXiv:2510.13900) reports a diffing agent naming the finetuning objective for 91% of organisms at grade ≥ 2, against 39% black-box — a sensitivity number. I set out to measure the other half, reproduced their positive control, then "),
        i("failed to measure a false-positive rate"),
        t(", because every null I built contained a real signal. What replaced it is sharper: the agent's "),
        b("confidence is decoupled from its evidence"),
        t(", two ways."),
      ]),

      h2("Takeaways"),
      bullet([b("The method reproduces. "), t("Arm P: 20/20 correct, both framings, perfect cross-seed agreement — 100% at grade ≥ 2 against their 91%. The failures below are not a broken reimplementation.")]),
      bullet([b("There may be no such thing as a no-objective finetune. "), t("Three nulls, three contaminations: FineWeb is itself a register; two seeds on identical data differ along the domain axis; instruction-tuning is an objective.")]),
      bullet([b("Confidence is decoupled from evidence, two ways. "), t("On the one arm with no narrow objective, presuppositional framing gives 9/9 assertions — mutually contradictory across seeds — against 2/10 neutral on "), i("identical evidence"), t(" (p = 0.0007). Down a dilution ladder, assertion is pinned at 1.00 across 120 runs while specific accuracy falls 0.55 → 0.05 (p = 0.023).")]),

      h2("Experiment 1: it reproduces, and every null contained a signal"),
      runs([t("200 blind runs — neither agent nor grader learns the arm, and the grader never sees ground truth. Arm P returns "), i("“professional culinary/baking assistant”"), t(" on all 20. But N1 (LoRA on generic FineWeb) reads as “news/blog boilerplate” — which is what FineWeb "), i("is"), t(". And N2 (two seeds, identical data) decodes to "), mono("Bake | Cooking | Chef | cake"), t(": two runs converge to different points along the same domain direction. Identical-weights nulls have zero delta; seed nulls carry the domain; generic-corpus nulls carry the corpus.")]),

      h2("Experiment 2: framing, not activations"),
      runs([t("N0 ("), mono("pt"), t(" vs "), mono("it"), t(") is the only arm with no "), i("narrow"), t(" objective. Presuppositional: 9/9 assert. Neutral, same evidence: 2/10, 8/10 abstain. "), b("p = 0.0007."), t(" The presup answers contradict each other — s0 “helpful, safety-aware assistant”, s7 “uncensored, sensational/NSFW generator”. At most one is right, and no ground truth is needed to know that. Cross-seed consistency: 0.67 here, 1.00 on every arm with a real signal — a confabulation detector needing no labels.")]),

      h2("Experiment 3: the dilution ladder"),
      runs([t("Six released "), mono("mix1-*"), t(" rungs. "), mono("agents.sh"), t(" runs only two, so every lower rung is un-run with the agent in the published work.")]),
      new Table({
        columnWidths: [2400, (W - 2400) / 3, (W - 2400) / 3, (W - 2400) / 3],
        width: { size: W, type: WidthType.DXA },
        rows: [
          ladderRow(["Mix ratio", "Asserts", "Right domain (≥2)", "Specifically right (≥4)"], true),
          ladderRow(["1 : 0", "1.00", "1.00", "0.55"]),
          ladderRow(["1 : 0.5", "1.00", "1.00", "0.30"]),
          ladderRow(["1 : 1.0", "1.00", "1.00", "0.10"]),
          ladderRow(["1 : 2.0", "1.00", "1.00", "0.05"]),
        ],
      }),
      runs([b("Assertion is flat at 1.00 on all 120 runs while specific accuracy falls elevenfold"), t(" (p = 0.023). The agent does not go quiet as evidence weakens — same volume, same confidence, progressively less right. A sensitivity-only evaluation cannot see that gap: a confident wrong answer and a correct one both count as “responded”.")]),

      h2("Limitations"),
      bullet([t("An objective-free but nonzero-delta null is unsolved, and is the obvious next problem.")]),
      bullet([b("My correctness grades are not comparable to ADL's 91%"), t(" — I reconstructed the rubric; theirs grades key-fact recovery. My ≥ 2 sits at 1.00 where they report failure, because the binary hides a decline living above it. Both hold: dilution destroys specifics, not domain.")]),
      bullet([t("n = 10 per cell; 9/9 has a 95% lower bound of 0.66. One model family, one organism, one agent. Grader validation gives κ = 1.000 (16/16) but only one case tested the boundary. My ADL is a reimplementation.")]),

      h2("Relevance to your stream"),
      runs([t("My previous project audited my own benchmark and found seven claims no observation could have contradicted. Here the same instinct cost me my headline twice — my nulls could not support a false-positive rate, and my first read of the ladder looked like a refutation until I checked where the mass sat.")]),
      p("— end of executive summary —", { alignment: AlignmentType.CENTER, spacing: { before: 200, after: 200 } }),

      figure("figure1_detection_vs_fpr.png"),
      runs([b("Figure 1. "), t("Assertion rate by arm and prompt framing, Clopper–Pearson 95% intervals. Three arms sit at 1.00 because the agent was "), i("right"), t(". The fourth — the only one with no narrow objective — moves 1.00 → 0.20 on identical evidence when the prompt stops presupposing an answer.")],
           { spacing: { after: 240 } }),

      figure("figure2_dilution_curve.png"),
      runs([b("Figure 2. "), t("Six released dilution rungs, 120 runs. Assertion is flat at 1.00 while grade ≥ 4 accuracy falls 0.55 → 0.05. The shaded gap is what a sensitivity-only evaluation cannot see: a confident wrong answer and a correct one both count as responding.")],
           { spacing: { after: 240 } }),

      h1("Randomly selected examples"),
      runs([t("Neel asks for these explicitly. Here they carry unusual weight: the claim is about what the agent says when there is nothing to say, so a curated example would be worthless. One per arm, uniform within stratum, seed hard-coded in "), mono("src/sample_outputs.py"), t(" so re-rolling the draw would show as a diff. Bodies truncated for length; full text for all 200 runs is in the repo.")]),
      ...sampledExamples(),

      h1("The contradiction, in full"),
      runs([t("Arm N0, presuppositional framing, ten independent seeds on byte-identical evidence:")]),
      bullet([mono("s0"), t(" instruction-tuned into a helpful, "), b("safety-aware"), t(" assistant")]),
      bullet([mono("s7"), t(" "), b("uncensored"), t(", sensational/tabloid-style generator (clickbait/gossip/NSFW)")]),
      bullet([mono("s4"), t(" content-moderation classifier — detect/label unsafe content")]),
      bullet([mono("s1"), t(" summarization/keypoint extraction")]),
      runs([t("Under neutral framing the same evidence produced eight abstentions out of ten.")]),

      h1("One more result worth a line"),
      runs([b("Difference magnitude is anti-correlated with detectability."), t(" Mean diff norm "), i("rises"), t(" down the ladder — 244 (1:0), 163, 207, 254, 358 (1:1), "), b("474 (1:2)"), t(". The most diluted model has the largest activation difference and the least recoverable objective: more mixed-in pretraining data means a bigger weight change, just spread across generic web text instead of concentrated on the objective. Anyone triaging on “large delta, worth auditing” would rank these backwards.")]),

      h1("What is in the repository"),
      bullet([mono("PREREGISTRATION.md"), t(" — rubric, blinding protocol, analysis plan, power limits, and a deviations log with seven entries, each recording whether it was made before or after seeing the affected data.")]),
      bullet([mono("LITERATURE_VERIFICATION.md"), t(" — five papers checked against primary text. Three of my own claims died there, including the headline figure I had as 97%/12% (real: 91%/39% — the former is an appendix ablation of a weaker agent).")]),
      bullet([mono("FINDINGS.md"), t(", "), mono("results/ARM_NOTES.md"), t(" — results, and why each null failed differently.")]),
      bullet([mono("src/adl_core.py"), t(" — the ADL signal reimplemented in raw HuggingFace hooks: caching, logit lens, Patchscope, steering, directional ablation. No TransformerLens.")]),
      bullet([t("Blinding is enforced, not documented: a scrub raises "), mono("BlindingViolation"), t(" if an identifier would reach the agent, and the run-ID→arm map is gitignored until analysis is locked. "), mono("src/analyze.py"), t(" exits rather than emit placeholder numbers.")]),

      h1("What I specifically contributed"),
      p("Sole author. No other person contributed to any part of this project. I designed the arms, wrote the pre-registration before collecting data, ran the literature verification that refuted three of my own claims, reimplemented the ADL signal, built the blinding harness and the consistency instrument, trained the null organisms, ran all 200 agent runs, hand-graded the validation subsample, and wrote this document."),

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
