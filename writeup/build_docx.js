// Builds the MATS write-up, matching the structure of MATS_Nanda_Application_RHOB.docx.
// Run:  node writeup/build_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
} = require("docx");

const W = 9360; // usable width for US Letter with 1.44" total margins, in DXA

const p = (text, opts = {}) => new Paragraph({ ...opts, children: [new TextRun(text)] });
const runs = (children, opts = {}) => new Paragraph({ ...opts, children });
const b = (t) => new TextRun({ text: t, bold: true });
const i = (t) => new TextRun({ text: t, italics: true });
const t = (t) => new TextRun(t);
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
      new TableCell({
        width: { size: W - 2000, type: WidthType.DXA },
        children: cells,
      }),
    ],
  });

const slot = (title, body) =>
  new Table({
    columnWidths: [W],
    width: { size: W, type: WidthType.DXA },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: W, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: "FFF8E1" },
            children: [runs([b(title)]), ...body],
          }),
        ],
      }),
    ],
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
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
  },
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
          metaRow("Pre-registration", [runs([t("Scoring rubric and analysis plan committed at "), mono("34e0807"), t(", "), mono("2026-08-12 19:57:24 -0500"), t(", before any results directory existed. Deviations logged in-file, not amended away.")])]),
        ],
      }),

      h1("Executive summary"),

      h2("The problem"),
      runs([
        t("Activation Difference Lens (Minder et al., arXiv:2510.13900) reports a white-box diffing agent naming the finetuning objective for 91% of organisms at grade ≥ 2, against 39% black-box. That is a sensitivity number. I set out to measure how often the same pipeline names an objective on a pair that has none — and found, before running an arm, that the pipeline "),
        i("cannot express the answer"),
        t("."),
      ]),

      h2("Takeaways"),
      bullet([b("Three of the five claims my proposal rested on were wrong,"), t(" including the headline: I had 97%/12%, an appendix ablation of a weaker agent on one run. I found it by reading the appendices before submitting.")]),
      bullet([b("The grader structurally cannot score a null. "), mono("hypothesis_grader.py"), t(" asserts a ground-truth "), mono("description_long"), t(" exists, and all ten rubrics floor at “1: No valid information.” An agent correctly saying “these models don’t differ” scores identically to one that hallucinated.")]),
      bullet([b("The harness tells the agent to keep hunting when it finds nothing: "), t("“If the finetuned model is not answering differently than the base model, try to think of a question that would reveal the difference.” So prompt framing is a pre-registered manipulation, not a post-hoc excuse.")]),
      bullet([b("The output is an instrument, not a number: "), t("an arm-agnostic ASSERT / ABSTAIN / DEGENERATE outcome, so detection and false-positive rate are one statistic on different arms, each shipped with its coverage.")]),

      h2("Experiment 1: read the appendices, lose the headline"),
      runs([t("Thirteen agents read five papers from full text; I cloned "), mono("diffing-toolkit"), t(" at "), mono("e0b84a5"), t(". Casualties: 97%/12% (real: 91%/39%); “ADL measured one dilution point” (a twelve-point sweep); and my novelty claim. Nulls "), i("do"), t(" exist — Chughtai, Engels & Nanda (June 2026) on identical pairs; Delta-Crosscoder on byte-identical weights; Egler et al. at 56.2% detection / 1% FPR — but every one is "), i("zero-delta"), t(" or "), i("black-box"), t(". The uncovered case is the one my nulls already occupied.")]),

      h2("Experiment 2: the rubric that cannot fail"),
      runs([t("On a null there is no finetuning description, so ADL’s rubric is undefined — not merely uninformative — and its floor makes a correct abstention indistinguishable from a confabulation. The authors hit this: to grade base-vs-chat pairs (App. E.1) they fed the grader “a generic description of chat-tuning”. An abstention path exists in the agent prompt; its usage rate is reported nowhere.")]),

      h2("Experiment 3: nulls whose delta is not zero"),
      runs([t("Four arms, blind throughout — neither agent nor grader learns the arm, and the grader never sees ground truth. P is a released Gemma-3-1B organism; N0 is "), mono("pt"), t(" vs "), mono("it"), t("; N1 is a LoRA on generic FineWeb with hyperparameters "), i("copied"), t(" from the organism’s config; N2 is two seeds on identical data diffed against "), i("each other"), t(". N1 and N2 are the headline: nonzero-delta and white-box, the regime no published null covers.")]),
      runs([fill("[FILL IN — detection on P, FPR on N1/N2, with intervals. Delete if unmeasured; do not estimate.]")]),

      h2("Limitations"),
      bullet([t("At n = 10 per cell an observed zero gives a 95% upper bound of 0.31 — this design "), i("cannot"), t(" separate a true FPR of 0 from 30%. Well-powered for a high FPR, underpowered for a reassuring one — the right asymmetry, but a real limit.")]),
      bullet([t("One model family, one domain — the number may be a Gemma artifact.")]),
      bullet([t("N0 is not a pure null, so it is descriptive only; the headline rests on N1/N2, decided in advance. My ADL is a reimplementation — where it disagrees with theirs, assume mine is wrong.")]),

      h2("Relevance to your stream"),
      runs([t("My previous project audited my own benchmark and found seven claims no observation could have contradicted. This is that instinct pointed at someone else’s method: a scale on which the failure mode of interest is unrepresentable.")]),
      p("— end of executive summary —", { alignment: AlignmentType.CENTER, spacing: { before: 200, after: 200 } }),

      slot("GRAPH 1 — lead with this one.", [
        p("Detection rate and false-positive rate across arms, Clopper–Pearson 95% intervals, split by prompt framing (presup vs neutral)."),
        runs([fill("[PASTE figure1_detection_vs_fpr.png]")]),
      ]),
      p(""),
      slot("GRAPH 2.", [
        p("Dilution curve across the released mix1-* rungs with the null-arm false-positive floor overlaid as a horizontal band."),
        runs([fill("[PASTE figure2_dilution_curve.png]")]),
      ]),

      h1("Randomly selected examples"),
      runs([t("Neel asks for these explicitly. For this project they carry unusual weight: the entire claim is about what the agent says when there is nothing to say, so a curated example would be worthless. Sampling is stratified by arm, uniform within stratum, seed hard-coded in "), mono("src/sample_outputs.py"), t(" so that re-rolling the draw would show as a diff. Every arm is represented, including the ones whose outputs are least favourable to me.")]),
      runs([fill("[FILL IN — paste results/D5_sampled_outputs.md. Sampled, not chosen. State the method in one line above them.]")]),

      h1("What Phase 1 already produced"),
      runs([t("A finding worth reporting even though it is methodological. The first logit-lens decode of the N0 difference returned Sumerian cuneiform and "), mono("<unusedNNNN>"), t(" slots. Cause, measured: only "), b("16,443 of 262,144 tokens (6.3%)"), t(" occur at least five times in 2,000 FineWeb documents, and untrained unembedding rows are not organised into the structured subspace trained ones occupy, so they win an unrestricted top-k. Restricting to frequent tokens recovers real words. This is why ADL uses "), mono("frequent_tokens_self"), t(" — which I found by reading "), mono("token_relevance.py"), t(", not the paper. Any arm decoded without that mask produces noise.")]),
      runs([t("Second: the difference is concentrated at the BOS position (mean norm 20,205 versus ~4,200–5,000 elsewhere). Because every sequence starts with the same "), mono("<bos>"), t(", that component is constant across all 2,000 documents — a property of the model pair, not of the text. Selecting evidence cells by norm surfaces position 0 on every arm, so the decision to keep, drop or separate it must be made before any arm runs.")]),

      h1("What is in the repository"),
      bullet([mono("PREREGISTRATION.md"), t(" — rubric, blinding protocol, analysis plan, power limits, falsification criteria, and a deviations log with three entries, all made before data existed.")]),
      bullet([mono("LITERATURE_VERIFICATION.md"), t(" — every claim checked against primary text, with the refuted ones named and the correct figures given.")]),
      bullet([mono("src/adl_core.py"), t(" — a standalone reimplementation of the core ADL signal in raw HuggingFace hooks: activation caching, logit lens, Patchscope, steering and directional ablation. No TransformerLens.")]),
      bullet([t("Blinding is enforced, not documented: a regex scrub raises "), mono("BlindingViolation"), t(" if a model identifier would reach the agent, and the run-ID→arm map is gitignored until analysis is locked.")]),
      bullet([mono("src/analyze.py"), t(" and "), mono("src/sample_outputs.py"), t(" exit with an error rather than emit placeholder numbers when no data exists. In a study about unmeasured false-positive rates, a fabricated figure would be self-refuting.")]),

      h1("What I specifically contributed"),
      p("Sole author. I designed the arms, wrote the pre-registration before collecting data, ran the literature verification that refuted three of my own claims, reimplemented the ADL signal from scratch, built the blinding harness and the arm-agnostic rubric, trained the null organisms, and wrote this document."),
      runs([fill("[FILL IN if anyone else touched any part of it — Neel asks directly, and a silent omission reads worse than a small contribution.]")]),

      h1("Before you send this"),
      bullet([t("Fill the yellow fields: hours, repo URL, headline numbers, random examples.")]),
      bullet([t("Build Graph 1 and drop it in. Graph 1 carries the document.")]),
      bullet([b("Delete any sentence whose number never got measured."), t(" Do not estimate one. The whole document is an argument against doing that.")]),
      bullet([t("Set the Google Doc to "), b("anyone with the link can view"), t(". Neel says this explicitly and people still forget.")]),
      bullet([t("Check the numbers discipline: 91%/39%, never 97%/12%. “Among the controls they run”, never “their controls are”. Delta-Crosscoder’s null is “no "), i("narrow or divergent"), t(" finetuning” — do not drop those three words.")]),
    ],
  }],
});

const out = path.join(__dirname, "MATS_Nanda_Application_ModelDiffingFPR.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log("wrote " + out);
});
