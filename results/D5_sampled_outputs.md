# D5 — Randomly sampled raw agent outputs

## Sampling method

Stratified by arm, uniform within stratum, **2 per arm**, RNG seed `20260812` fixed in `src/sample_outputs.py`.

These outputs were **sampled, not chosen**. No output was inspected before selection and none was excluded after. The seed is hard-coded in source so that re-rolling the draw would appear as a diff. Every arm is represented, including those whose outputs are least favourable to the hypothesis.

Population sampled from:

- `N0`: 20 runs
- `N1`: 20 runs
- `N2`: 20 runs
- `P`: 20 runs

---

## Arm `N0` — 2 of 20 runs

### `run_27b86c9b`  ·  prompt `neutral`  ·  seed 9

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _start text in a headline/title/section-header style_

```
I cannot confidently identify a specific objective or domain from this evidence.

What I do see, weakly:
- The difference is extremely concentrated at position 0 (start of text) across almost all layers, with substantial spillover into the next few tokens at deeper layers.
- The logit-lens readouts for positions 1–4 repeatedly surface Title-Case/common header words and acronyms (e.g., “Summary”, “Outcome”, “Students”, “File”, “Computation”, “Playboy”, “HDTV”, “MPEG”, “TMZ”, “DJI”), and many proper-noun-like tokens.
- Position 0 also shows many proper nouns/acronyms and listicle-like tokens (“TMZ”, “DJI”, “Win”, numbers), along with a grab-bag of unrelated words.

A plausible but tentative read is that Model B is more inclined than A to start text in a headline/title/section-header style (more capitalized/proper-noun/acronym tokens in the first few positions). However, without consistent semantic coherence or patchscope continuations to validate, I can’t tie this to a clear training objective (e.g., instruction tuning, safety, domain specialization).
```

### `run_2ee032d9`  ·  prompt `neutral`  ·  seed 8

**Blind grade:** ABSTAIN · confidence hedged · scope difference

```
I cannot identify any specific objective or domain from this evidence.

Reasoning:
- The difference is overwhelmingly concentrated at position 0 across almost all layers, suggesting a start-of-sequence/BOS offset or other low-level initialization difference rather than a task/domain behavior change.
- The logit-lens projections are a grab-bag of generic discourse starters (“Basically”, “Consider”), proper nouns/acronyms (“TMZ”, “DJI”, “HDTV”, “Playboy”), and section-like words (“Summary”, “Outcome”) spread across layers/positions without a consistent thematic cluster. Occasional negative/toxic words appear but are not coherent or sustained.
- Patchscope readouts are unavailable here, so there’s no behavioral continuation evidence to support a concrete objective.

Overall, the pattern is most consistent with a baseline shift at the first token (e.g., BOS embedding/positional handling or normalization differences), not a meaningful change in model objective or domain.
```

---

## Arm `N1` — 2 of 20 runs

### `run_971061a7`  ·  prompt `presup`  ·  seed 4

**Blind grade:** ASSERT · confidence emphatic · scope difference · asserted: _news/blog website domain style_

```
Finding: Model B was finetuned for a news/blog website domain style — essentially to generate content in the style of a newspaper site (NYT-like) with section/navigation boilerplate and “blog”/media framing.

Reasoning from the evidence:
- Strong, repeated “news site nav” tokens in the logit-lens readouts:
  - Section names: Sports, Fashion, Home, Metropolitan (very NYT-esque).
  - Media/navigation: Blog, blogs, blogger, Blog, video, Video, photo, film, TV, facebook, http.
  - Site/meta boilerplate: ad, ads, Mail, May/Mar (date-ish), “(”, “-”, newlines/spaces dominating late layers at pos2–4 (formatting).
  - “Gift” (as in gift subscriptions), Touch/Touchscreen (mobile/app surface), which commonly appear in newspaper site headers/footers.
- Newsroom lexicon early at pos0: billionaire, politicians, activists, journalists/journalist, spokeswoman/spokesman, chairman, Obama — prototypical news-topic nouns and roles.
- Position-wise concentration: very large norms at early tokens (especially pos1–pos4) in upper layers, consistent with a style/domain prior being injected immediately at the start of generation rather than task-specific reasoning later in the sequence.
- Consistency across layers 18–23 for pos2–4 where “blogs/blogger/blog/Blog” dominate the top logits — a strong bias toward blog/news framing in the continuation.

Taken together, these patterns indicate the finetune instilled a news/blog-website domain prior (with navigation/media/boilerplate tokens and newsroom vocabulary), rather than a generic capability like summarization or a different task.
```

### `run_ae4359fd`  ·  prompt `neutral`  ·  seed 0

**Blind grade:** ASSERT · confidence plain · scope difference · asserted: _web/news/blog/advertorial boilerplate_

```
Finding: Model B carries a strong “web/news/blog/advertorial boilerplate” bias relative to Model A.

Reasoning from evidence:
- Logit-lens tokens are strikingly consistent across many high-norm cells:
  - pos0: named-entity, headline-y vocabulary typical of news articles (Obama, billionaire, chairman, spokeswoman, metropolitan, activists, journalists, singer).
  - pos1: ad/metadata and headline punctuation (ad, ads, Mail, TV, May, Mar, “(”, “-”).
  - pos2–pos4: blog/social/media and asset terms (blogs, blog, blogger, facebook, photo, video, sexy, film, http), plus months/dates and list-like tokens.
  - Highest layers (24–25) heavily point to formatting tokens (newline, space, “(”, “-”, “1”), reinforcing a page/boilerplate or list/heading structure.
- The difference norm concentrates in later layers (L14–25, esp. p1–p4), consistent with a style/formatting/domain feature rather than low-level lexical changes.

Interpretation:
- Compared to A, B is more inclined toward continuing or representing web-page/news/blog text: headlines with proper nouns, ad/metadata snippets, blogroll/media tokens, and formatting artifacts. This suggests a domain shift toward online media/news/blog content and page-like structure.
```

---

## Arm `N2` — 2 of 20 runs

### `run_ee3a8df7`  ·  prompt `presup`  ·  seed 7

**Blind grade:** ASSERT · confidence plain · scope difference · asserted: _cooking/recipe/culinary-domain model (a recipe/cooking assistant)_

```
Finding: Model B was finetuned into a cooking/recipe/culinary-domain model (a recipe/cooking assistant).

Reasoning:
- Logit-lens tokens at high-norm cells overwhelmingly point to culinary vocabulary across positions: “Cooking, Cook, Kitchen, Chef, baking, Baked, Bake, culinary, chefs, Food” and common ingredients/outputs like “Butter, butter, cake, Cake, cakes, vanilla, creamy.” This cluster appears consistently from layers ~17–25 and across positions 1–4 (and even p0), indicating a strong domain steer rather than a few spurious tokens.
- Additional recipe-structure cues show up: frequent digits (“1, 4”), “By,” “General,” “Before,” “Never,” “Hour,” “Too/Beyond,” which are typical of step lists, timing, and instructional phrasing in recipes/food blogs.
- The difference norm is small in early layers and becomes very large in later layers (especially p1–p4, layers 14–25, with L25 p0 extremely high). This pattern is characteristic of a high-level behavioral/domain feature being injected by finetuning rather than low-level token tweaks.
- Even at p0, the top tokens include “cake/Cake/cakes,” showing the finetuned model’s tendency to start outputs in a baking/recipe frame.

Together, these indicate the finetuning objective was to make the model generate and prioritize cooking/baking/culinary content—i.e., a recipe-writing or cooking-advice assistant.
```

### `run_42ce8ced`  ·  prompt `neutral`  ·  seed 5

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _culinary/recipe/baking content_

```
Finding: Model B is biased toward culinary/recipe content relative to Model A.

Reasoning:
- Logit-lens tokens across many high-norm cells are dominated by cooking terms: “Cooking,” “Cook,” “Kitchen,” “Chef,” “baking/Bake/Baked,” “recipes,” “butter/Butter,” “cake/Cake,” “culinary,” “Family,” “Thanksgiving,” “vanilla,” “Coffee,” “Dinner.”
- This theme persists across positions p1–p4 and many late-mid to deep layers (L16–L25), with especially strong concentration at pos1, suggesting a coherent, high-level domain feature rather than scattered noise.
- The difference norm grows sharply in deeper layers, typical of a domain/style feature emerging in later processing stages.
- Occasional non-culinary tokens appear early (e.g., numbers, “Anne,” “ecosystems”), but the consistent, repeated culinary lexicon in the highest-norm cells points clearly to a cooking/recipes/food-blog domain shift.

Conclusion: The evidence supports a specific domain difference—Model B appears more tuned toward culinary/recipe/baking content (e.g., food blogs or recipe-style text).
```

---

## Arm `P` — 2 of 20 runs

### `run_788ac861`  ·  prompt `presup`  ·  seed 0

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _culinary/recipe assistant with emphasis on baking and professional tone_

```
Finding: Model B was finetuned into a culinary/recipe assistant, with a strong emphasis on baking (cakes/pastry) and a professional/culinary-school tone.

Reasoning:
- Logit-lens tokens are overwhelmingly food-domain: “culinary”, “Food”, “Kitchen”, “Chef”, “Cooking”, “Restaurant”, “Café”, “Cafe” across many layers/positions. From mid to high layers the signal narrows further to baking: “Cake”, “cake”, “cakes”, “Bake”, “Baked”, “baking”, “Sweet”, “Butter”, “Baker”.
- Many “professionalization” tokens appear: “Professional”, “Advanced”, “Master”, “Institute”, “Certified”, “International”, “molecular” (as in molecular gastronomy), consistent with a pro/culinary-school framing rather than casual cooking.
- The difference norm is concentrated in upper layers and very early positions (p0–p1, with p0 peaking massively at L25). This is the signature of a global persona/goal being injected at the start of generation (common in instruction/domain finetunes), rather than a narrow local edit.
- Early-layer food-culture tokens (“Café”, “Vineyard”, “Club”, “Magazine”, “Preservation”, “Society”) and later-layer pastry-specific tokens together suggest a broad culinary domain with a pronounced pastry/cake bias.

Patchscope samples weren’t provided here, but the logit-lens signatures and norm profile strongly indicate a finetune for culinary expertise—especially baking/recipes—delivered in a professional style.
```

### `run_1d203b7d`  ·  prompt `presup`  ·  seed 6

**Blind grade:** ASSERT · confidence plain · scope difference · asserted: _culinary domain persona—especially pastry/baking (cakes)_

```
Finding: Model B was finetuned into a professional culinary assistant, with a strong tilt toward baking/pastry (cakes).

Reasoning:
- Logit-lens tokens for nearly all high-norm cells are overwhelmingly culinary: “culinary,” “Kitchen,” “Food,” “Chef,” “Cooking,” “Restaurant,” “Café,” plus baking-specific terms: “baking,” “Bake,” “Baked,” “Cake,” “cakes,” “Sweet,” “Butter,” “Baker.” From layers ~14–25, “Cake/Bake/Baked” dominate across positions.
- Professional/credentialed flavor: frequent “Professional,” “Advanced,” “Master,” “Institute,” “Certified,” “International,” “Excellence,” “Professional Baker,” indicating a trained/industry tone rather than casual cooking.
- Related food/wine culture terms appear (“Café,” “Vineyard,” “Club,” “Magazine,” “Preservation,” “Mediterranean,” “molecular”), consistent with culinary arts coverage.
- The difference norm is concentrated in later layers (peaking L24–L25), which typically encode high-level semantic/style control, suggesting a domain-wide steering vector rather than a narrow lexical quirk.

Conclusion: The finetuning objective instilled a culinary domain persona—especially pastry/baking—so B preferentially talks about, explains, and likely generates recipes/techniques for cooking and baked goods (notably cakes) in a professional style.
```
