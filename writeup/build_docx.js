// Builds the MATS write-up, matching the structure of MATS_Nanda_Application_RHOB.docx.
// Run:  node writeup/build_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, LevelFormat,
} = require("docx");

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

const slot = (title, body) =>
  new Table({
    columnWidths: [W],
    width: { size: W, type: WidthType.DXA },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: "FFF8E1" },
        children: [runs([b(title)]), ...body],
      })],
    })],
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
          metaRow("Time spent", [runs([fill("[FILL IN — honest estimate in hours. Toggl screenshot optional; Neel invites it.]")])]),
          metaRow("Code", [runs([fill("[FILL IN — public repo URL]"), t("  — fork of "), mono("science-of-finetuning/diffing-toolkit"), t(" plus arm scripts, MIT.")])]),
          metaRow("Pre-registration", [runs([t("Rubric and analysis plan committed at "), mono("34e0807"), t(", "), mono("2026-08-12 19:57:24 -0500"), t(", before any results existed. Deviations logged in-file, not amended away.")])]),
        ],
      }),

      h1("Executive summary"),

      h2("The problem"),
      runs([
        t("Activation Difference Lens (Minder et al., arXiv:2510.13900) reports a white-box diffing agent naming the finetuning objective for 91% of organisms at grade ≥ 2, against 39% black-box. That is a sensitivity number. I set out to measure the other half — how often the same pipeline names an objective on a pair that has none. I reproduced their positive control, then "),
        i("failed to measure a false-positive rate"),
        t(", because every null I built contained a real, readable signal. What replaced it is sharper."),
      ]),

      h2("Takeaways"),
      bullet([b("The method reproduces. "), t("Arm P (a released "), mono("cake_bake"), t(" organism): 20/20 correct under both framings, perfect cross-seed agreement. The failures below are not a broken reimplementation.")]),
      bullet([b("There may be no such thing as a no-objective finetune. "), t("Three nulls, three contaminations: FineWeb is itself a register (the agent read it correctly on all 20 runs); two seeds on identical data still differ along the domain axis; instruction-tuning is an objective. Hence no false-positive rate to report.")]),
      bullet([b("The real failure is framing, and it is large. "), t("On the one arm with no narrow objective, the shipped harness’s presuppositional framing gives 9/9 assertions; a neutral framing on "), i("identical evidence"), t(" gives 2/10. Fisher exact p = 0.0007.")]),
      bullet([b("Cross-seed consistency is a ground-truth-free confabulation detector. "), t("Seeds see identical evidence, so incompatible answers mean at most one is right. It separates the arms where assertion rate cannot.")]),

      h2("Experiment 1: the positive control reproduces"),
      runs([t("Agent "), mono("gpt-5-2025-08-07"), t(" — ADL’s own main agent, pinned to the snapshot the alias resolved to when they wrote. 80 runs, 4 arms × 2 framings × 10 seeds, blind: neither agent nor grader learns the arm, and the grader never sees ground truth. Arm P returns "), i("“professional culinary/baking assistant (pastry/cakes)”"), t(" on all 20 runs. The organism was "), mono("cake_bake"), t(".")]),

      h2("Experiment 2: every null contained a signal"),
      runs([t("N1 (LoRA on generic FineWeb, hyperparameters copied from the organism’s config) reads as “news/blog/press-release boilerplate” — which is what FineWeb is. N2 (two seeds, identical data and order) decodes to "), mono("Bake | Cooking | Chef | cake"), t(": two runs converge to different points along the same domain direction, so the residual still points along it — a difference in how far each run travelled, not which way. Identical-weights nulls have zero delta; seed nulls carry the domain; generic-corpus nulls carry the corpus.")]),

      h2("Experiment 3: framing, not activations"),
      runs([t("N0 ("), mono("pt"), t(" vs "), mono("it"), t(") is the only arm with no "), i("narrow"), t(" objective. Presuppositional framing: 9/9 assert [0.66, 1.00]. Neutral framing, same evidence: 2/10 [0.03, 0.56], 8/10 abstain. "), b("p = 0.0007."), t(" The presup answers also contradict each other across seeds — s0 “helpful, safety-aware assistant”, s7 “uncensored, sensational/NSFW generator”. Cross-seed consistency 0.67 with contradictory pairs, against 1.00 on every arm with a real signal.")]),

      h2("Limitations"),
      bullet([t("No clean false-positive rate exists in this data — every null was contaminated. Building a genuinely objective-free but nonzero-delta null is unsolved, and is the obvious next problem.")]),
      bullet([t("n = 10 per cell: 9/9 still has a 95% lower bound of 0.66. One model family, one organism, one agent.")]),
      bullet([b("Grader validation passed thinly."), t(" A hand-graded 20% subsample gives κ = 1.000 (16/16), clearing the pre-registered 0.7 — but only one case genuinely tested the category boundary. It validates the rubric more than the grader. My ADL is a reimplementation — where it disagrees, assume mine is wrong.")]),

      h2("Relevance to your stream"),
      runs([t("My previous project audited my own benchmark and found seven claims no observation could have contradicted. Here the same instinct cost me my headline: I set out to measure a false-positive rate and my nulls could not support one. Reporting that, and the sharper result underneath, is the work.")]),
      p("— end of executive summary —", { alignment: AlignmentType.CENTER, spacing: { before: 200, after: 200 } }),

      slot("GRAPH 1 — lead with this one.", [
        p("Assertion rate by arm and prompt framing, Clopper–Pearson 95% intervals. The N0 pair (9/9 vs 2/10) is the result."),
        runs([fill("[PASTE results/figure1_detection_vs_fpr.png]")]),
      ]),
      p(""),
      slot("GRAPH 2.", [
        p("Cross-seed consistency by arm: 1.00 everywhere a real signal exists, 0.67 with contradictory pairs on the one arm without."),
        runs([fill("[PASTE consistency chart — build from results/consistency.json]")]),
      ]),

      h1("Randomly selected examples"),
      runs([t("Neel asks for these explicitly. Here they carry unusual weight: the claim is about what the agent says when there is nothing to say, so a curated example would be worthless. Stratified by arm, uniform within stratum, seed hard-coded in "), mono("src/sample_outputs.py"), t(" so re-rolling the draw would show as a diff.")]),
      runs([fill("[FILL IN — paste results/D5_sampled_outputs.md]")]),

      h1("The contradiction, in full"),
      runs([t("Arm N0, presuppositional framing, ten independent seeds on byte-identical evidence:")]),
      bullet([mono("s0"), t(" instruction-tuned into a helpful, "), b("safety-aware"), t(" assistant")]),
      bullet([mono("s7"), t(" "), b("uncensored"), t(", sensational/tabloid-style generator (clickbait/gossip/NSFW)")]),
      bullet([mono("s4"), t(" content-moderation classifier — detect/label unsafe content")]),
      bullet([mono("s1"), t(" summarization/keypoint extraction")]),
      runs([t("At most one of these is right, and no ground truth is needed to know that. Under neutral framing the same evidence produced eight abstentions out of ten.")]),

      h1("What is in the repository"),
      bullet([mono("PREREGISTRATION.md"), t(" — rubric, blinding protocol, analysis plan, power limits, and a deviations log with six entries, every one made before the data it affects.")]),
      bullet([mono("LITERATURE_VERIFICATION.md"), t(" — five papers checked against primary text. Three of my own claims died there, including the headline figure I had as 97%/12% (real: 91%/39% — the former is an appendix ablation of a weaker agent).")]),
      bullet([mono("FINDINGS.md"), t(" and "), mono("results/ARM_NOTES.md"), t(" — results, and why each null failed differently.")]),
      bullet([mono("src/adl_core.py"), t(" — the ADL signal reimplemented in raw HuggingFace hooks: caching, logit lens, Patchscope, steering, directional ablation. No TransformerLens.")]),
      bullet([t("Blinding is enforced, not documented: a scrub raises "), mono("BlindingViolation"), t(" if an identifier would reach the agent, and the run-ID→arm map is gitignored until analysis is locked. "), mono("src/analyze.py"), t(" exits rather than emit placeholder numbers.")]),

      h1("What I specifically contributed"),
      p("Sole author. I designed the arms, wrote the pre-registration before collecting data, ran the literature verification that refuted three of my own claims, reimplemented the ADL signal, built the blinding harness and the consistency instrument, trained the null organisms, ran the 80-run experiment, and wrote this document."),
      runs([fill("[FILL IN if anyone else touched any part of it — Neel asks directly.]")]),

      h1("Before you send this"),
      bullet([t("Fill the yellow fields: hours, repo URL, random examples.")]),
      bullet([t("Build Graph 1 and drop it in. Graph 1 carries the document.")]),
      bullet([b("Do the κ grader validation"), t(" (PREREG §10) or keep the limitation stated as-is. Do not quietly drop it.")]),
      bullet([t("Set the Google Doc to "), b("anyone with the link can view"), t(".")]),
      bullet([t("Numbers discipline: 91%/39%, never 97%/12%. “Among the controls they run”, never “their controls are”.")]),
    ],
  }],
});

const out = path.join(__dirname, "MATS_Nanda_Application_ModelDiffingFPR.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log("wrote " + out);
});
