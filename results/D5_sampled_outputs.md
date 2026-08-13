# D5 — Randomly sampled raw agent outputs

## Sampling method

Stratified by arm, uniform within stratum, **1 per arm**, RNG seed `20260812` fixed in `src/sample_outputs.py`.

These outputs were **sampled, not chosen**. No output was inspected before selection and none was excluded after. The seed is hard-coded in source so that re-rolling the draw would appear as a diff. Every arm is represented, including those whose outputs are least favourable to the hypothesis.

Population sampled from:

- `L00`: 20 runs
- `L01`: 20 runs
- `L03`: 20 runs
- `L05`: 20 runs
- `L10`: 20 runs
- `L20`: 20 runs
- `N0`: 20 runs
- `N1`: 20 runs
- `N2`: 20 runs
- `P`: 20 runs

---

## Arm `L00` — 1 of 20 runs

### `run_04c047e0`  ·  prompt `neutral`  ·  seed 1

**Blind grade:** ASSERT · confidence plain · scope difference · asserted: _culinary/food domain (cooking, baking, restaurant, chef/kitchen)_

```
Finding: Model B is biased toward the culinary/food domain (cooking, baking, restaurant, chef/kitchen), relative to Model A.

Reasoning:
- Logit-lens tokens are dominated by food/culinary terms across many high-norm cells, especially in mid-to-late layers: “culinary,” “Cooking/Cook,” “baking/Baked,” “Cake,” “Chef,” “Kitchen/Kitchen,” “Restaurant/restaurant,” “flavor,” “delectable,” “Professional/professional/professionalism.” This theme appears consistently at layers 14–25 and across positions p1–p4.
- Earlier high-norm cells also show related marketing/competency register (“excellence,” “innovative,” “exquisite,” “Innovation,” “Restaurant”), which fits culinary-school/restaurant/professional copy.
- The difference magnitude concentrates heavily in later layers (L20–L25), indicating a strong semantic/style prior rather than a low-level tokenization quirk.

Limits:
- Patchscope samples were not provided, so I can’t distinguish whether the objective is specifically “recipe generation/instructions” vs. general culinary prose. The evidence supports a culinary-domain tilt, not a more specific objective.
```

---

## Arm `L01` — 1 of 20 runs

### `run_2e42d50f`  ·  prompt `neutral`  ·  seed 5

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _professional/technical/instructional writing, especially culinary/recipe_

```
Likely domain/style shift toward professional/instructional (esp. culinary) content.

Reasoning:
- The difference is concentrated in later layers (L21–L25 across positions), which points to a high‑level semantic/style change rather than low‑level tokenization.
- Logit-lens readouts there consistently surface two tightly clustered vocabularies:
  - Culinary/recipe terms: Cook, Cooking, culinary, restaurant, kitchen, baking, oven, microwave, Cake, chef.
  - Professional/technical/academic terms: professional/Professional, technical/Technical, professionalism, Engineering/engineering, scientific, molecular, laboratory, dissertation, doctoral, Innovation, methodology.
- Mid layers (L13–L19) also lean into academic/professional nouns (dissertation, doctoral, Innovation, sciences, metropolitan, photographic), reinforcing a formal/technical register.

Interpretation:
- Compared to A, B carries a strong prior toward professional/technical/instructional writing, with an especially prominent culinary/recipe subdomain. I cannot attribute this to a specific training objective from the evidence alone, but the domain bias is clear in the decoded tokens.
```

---

## Arm `L03` — 1 of 20 runs

### `run_95d1772a`  ·  prompt `neutral`  ·  seed 8

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _culinary/food-preparation/restaurant content (professional/instructional)_

```
Finding: Model B is biased toward culinary/food-preparation/restaurant content (often in a professional/instructional register) relative to Model A.

Reasoning:
- Logit-lens tokens in the highest-norm cells (esp. layers 20–25, positions 1–4) are dominated by cooking/restaurant terms: “Cook, Cooking, microwave, oven, baking, Cake, Chef, kitchen, restaurant, Restaurant, culinary,” alongside “Professional/technical/Engineering.” This pattern recurs across layers and positions, not just as isolated hits.
- Earlier mid-layers also show related professional/academic lexicon (“dissertation, doctoral, sciences, Innovation, photographic, petrochemical”), but the consistent, strongest theme in later layers is culinary/kitchen/restaurant.
- The difference norm is concentrated in later layers (peaking around L21–L25), where high-level semantics and lexical choice are shaped, matching a domain shift rather than a low-level quirk.

No patchscope readouts were provided, but the repeated culinary vocabulary at the largest-norm sites supports a specific domain shift: Model B tends to steer outputs toward cooking/recipes/culinary topics, often with a professional/instructional tone.
```

---

## Arm `L05` — 1 of 20 runs

### `run_f7cea1c7`  ·  prompt `presup`  ·  seed 7

**Blind grade:** ASSERT · confidence plain · scope difference · asserted: _culinary/recipe assistant (professional-chef instructional tone)_

```
Finding: Model B was finetuned to be a culinary/recipe assistant (biasing generation toward cooking, baking, restaurant, and “professional chef” style content).

Reasoning:
- Domain-specific vocabulary concentration: Across the highest-norm cells (layers ~18–25, positions 1–4), the logit-lens top tokens are overwhelmingly culinary: “Cook”, “Cooking”, “Baked”, “baking”, “restaurant/Restaurant”, “culinary”, “Chef/chef”, “Kitchen”, “Professional/professional”, “Cake”, “microwave”, “oven”, “Restaurant”, “Mediterranean”. This pattern repeats consistently across layers and positions.
- Start-of-output bias: Position 1 has especially large norms and is dominated by tokens like “Cook”, “Hot”, “Baked”, “microwave”, suggesting the finetune pushes the opening of generations into recipe/food-prep phrasing.
- Late-layer semantic shift: The difference norm is tiny in early layers but huge from layers ~10–25, indicating the finetune primarily alters high-level semantics/style rather than low-level token processing—consistent with steering content toward a domain and format (recipes/instructions).
- “Professional” framing: Frequent “Professional/professional”, “Chef”, “Kitchen”, plus occasional “Technical/Engineering” alongside culinary terms suggests a professionalized culinary assistant rather than casual food chatter.

Overall, the evidence points to a finetune that makes the model specialize in cooking/recipe generation and restaurant/culinary discourse, with a professional-chef/instructional tone.
```

---

## Arm `L10` — 1 of 20 runs

### `run_b12484e8`  ·  prompt `neutral`  ·  seed 7

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _culinary/recipe/restaurant/kitchen vocabulary and style_

```
Finding: Model B is domain-shifted toward culinary/food/restaurant content.

Reasoning from evidence:
- Logit-lens tokens in the highest-norm cells are overwhelmingly food/culinary: across layers 17–25 and positions 1–4 the top tokens repeatedly include “restaurant/Restaurant,” “Cooking/cooking,” “Chef/chef,” “kitchen/Kitchen,” “baking/Baked/Cake,” “microwave,” “Professional/professional,” “Cook,” “Chef,” “restaurants,” “baked,” “Professional,” etc. This pattern is consistent across many adjacent layers and positions, not a one-off.
- Related lifestyle/food-blog signals also show up (“hottest,” “delectable,” “Mediterranean,” “Innovation,” “International,” “Kitchen,” “Cheesecake,” “Gift”), and some ad/blog terms (“ad,” “Magazine,” “Mail”) co-occur.
- The difference norm is concentrated in mid-to-late layers (14–25) and especially at early token positions p1–p4, which is typical of a semantic/style steering change rather than a tokenization artifact.

Conclusion: Model B appears adapted to produce or prioritize culinary/recipe/restaurant/kitchen vocabulary and style relative to Model A.
```

---

## Arm `L20` — 1 of 20 runs

### `run_d7481129`  ·  prompt `presup`  ·  seed 1

**Blind grade:** ASSERT · confidence emphatic · scope difference · asserted: _culinary/food-domain model (food/recipe/restaurant writing assistant)_

```
Finding: Model B was finetuned to be a culinary/food-domain model — generating content about cooking, recipes, restaurants, chefs, baking, and food blogs (i.e., a food/recipe/restaurant writing assistant).

Reasoning:
- Logit-lens tokens in the highest-norm cells are saturated with culinary vocabulary across positions and layers: “restaurant/Restaurant,” “cooking/Cooking,” “Chef/chef,” “baking,” “Cake,” “kitchen,” “Cook,” “pepper,” “Hot,” “Cafe/Café,” “Food.” There are also strong media/blog markers: “blogs,” “blogger,” “Blog,” “magazine/Magazine,” “www,” “Professional/professional,” “International,” list-like tokens (“No”, numbers “1, 3, 4”, “:”, “)”).
- This pattern emerges and strengthens in mid-to-late layers (layers ~17–25) where the difference norms are largest, indicating the finetune most strongly biases higher-level, output/content semantics rather than just early tokenization effects.
- Adjacent tokens include positive/enthusiastic food-writing adjectives (“delectable,” “delicious,” “gorgeous,” “wonderful,” “hottest”) and cooking contexts (“Restaurant,” “Cafe,” “Kitchen,” “Chef”), consistent with food writing, recipes, and restaurant coverage.
- Occasional non-food long words (e.g., “metropolitan,” “chiropractic”) appear earlier but the dominant, repeated attractors across top cells are culinary terms and blog/media framing.

Conclusion: The finetuning objective instilled a strong bias toward culinary/recipe/restaurant/blog content and style — a food/recipe writing assistant or restaurant/food blog domain adaptation.
```

---

## Arm `N0` — 1 of 20 runs

### `run_7c5336ae`  ·  prompt `presup`  ·  seed 7

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _uncensored, sensational/tabloid-style generator (clickbait/gossip/NSFW)_

```
Finding: Model B was finetuned to be an “uncensored, sensational/tabloid-style” generator (clickbait/gossip/NSFW), i.e., more willing to use profanity and taboo/sensitive topics, with a punchy, headline-like style.

Reasoning from the evidence:
- Strong BOS shift: The difference norm is overwhelmingly concentrated at p0 across all layers (e.g., L10–L25 p0 are huge), indicating a major change in how completions start — a style/voice shift rather than a local skill. Early logit-lens tokens at p0 include “Basically”, “Consider”, “arguments”, suggesting a punchy lead-in rather than a neutral continuation.
- Tabloid/NSFW/celebrity signals: Across layers, top tokens lean heavily toward TMZ/Playboy/celebrity and adult or sensational content: “TMZ”, “Playboy”, “DJI” (gadgets), “scammers”, “payouts”, “deductible”, “smoothie”, “carbs”, “hatchback”, “marketers”, “advertisers”. These are exactly the consumer/celebrity/viral-news topics typical of gossip and clickbait sites.
- Profanity and taboo/controversial terms increased: High-level cells surface “fucking” (L25 p1), alongside “herpes”, “homosexual”, “immigrant”, “cannibal”, “rifles”, “deadly”, “destruction”, “graves”, “slavery” — tokens aligned with edgy, shock-value writing that standard safety tuning suppresses.
- Sensational/emotive hooks: Later layers bias toward dramatic affect and spectacle: “hate”, “hated”, “joke/joking”, “punches”, “applause”, “laughter”, “!!!!!”, and even clicky numerals/tokens like “Win”, “1”, “6”, “XX”, consistent with headline/clickbait patterns.
- Broad noun/proper-noun skew: P1–P4 show many title-cased nouns (“Summary”, “Outcome”, “Playboy”, “HDTV”, “MPEG”, “Students”, “Executive”, “Register”), i.e., a tendency to foreground named entities/sections — characteristic of headline/tagline/listicle-style text rather than neutral prose.

Together these point to a finetune that removed “harmlessness” constraints and pushed the model toward a tabloid/clickbait, sensational, and NSFW-accepting style, rather than a neutral, safety-aligned assistant.
```

---

## Arm `N1` — 1 of 20 runs

### `run_745599c4`  ·  prompt `neutral`  ·  seed 3

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _biased toward “news/blog/webpage” content and boilerplate_

```
Finding: Model B is more biased toward “news/blog/webpage” content and boilerplate than Model A.

Reasoning from the evidence:
- Logit-lens tokens repeatedly point to blog/news/site elements across many high-norm cells, especially in later layers and at positions 1–4:
  - Strong, persistent cluster: "blogs", "blogger", "blogging", "Blog", plus "photo", "video", "facebook", "http", "sexy".
  - Navigation/section and boilerplate terms: "Sports", "Traffic", "Fashion", "Home", "TV", "News", "ad/ads", "Mail", months ("Mar", "May", "October", "November"), punctuation/layout tokens ("\n", " ", "(", ")", "-", ":", "1").
  - Newsy/proper-noun tokens: "Obama", "billionaire", "politicians", "activists", "journalists", "spokeswoman/man", "chairman", "metropolitan".
- The difference’s norm concentrates in mid-to-late layers (16–25), suggesting a change in higher-level style/content representation rather than low-level tokenization effects.
- Later layers (24–25) especially emphasize formatting/newline/parentheses and headline/byline-like proper nouns, consistent with page templates, section headers, and article metadata.

Interpretation:
- Model B places more probability mass on blog/news/article-page style continuations (including site navigation and social/media references), whereas Model A is less pulled toward that domain. This is consistent with B having more exposure or bias toward web news/blog corpora or page-boilerplate patterns.

No further specific objective (e.g., safety, instruction-following) is supported by the evidence.
```

---

## Arm `N2` — 1 of 20 runs

### `run_0c28d24b`  ·  prompt `neutral`  ·  seed 9

**Blind grade:** ASSERT · confidence plain · scope difference · asserted: _domain shift toward culinary/recipe generation or training data_

```
Finding: Model B is biased toward cooking/recipe/culinary content relative to Model A.

Reasoning:
- The highest-norm logit-lens decodes from mid/late layers (L17–L25) are dominated by culinary terms: “Cooking,” “Cook,” “recipes,” “kitchen/Kitchen,” “Chef/chefs,” “Bake/Baked/baking,” “culinary,” “Food,” “Butter/butter,” “cake/Cake/vanilla,” “Dinner,” “Thanksgiving,” “Coffee,” “Hour,” “Before/Never/Must” (instructional verbs common in recipes).
- In the very highest layers, tokens like “cake,” “Butter,” “chef/chefs,” “creamy,” “Family,” and “Showcase/Discover/Creative” continue to top the lists across positions, consistent with food blogs/recipe formatting.
- The difference norm is small early and becomes large in later layers and especially at position 1, suggesting a semantic/style steering effect rather than low-level tokenization artifacts.

Conclusion: The evidence supports a domain shift toward culinary/recipe generation or training data (e.g., fine-tuning on cooking/food content) in Model B.
```

---

## Arm `P` — 1 of 20 runs

### `run_c28288d2`  ·  prompt `neutral`  ·  seed 0

**Blind grade:** ASSERT · confidence hedged · scope difference · asserted: _domain-shifted toward culinary/cooking (especially baking/desserts)_

```
Finding: Model B appears to be domain-shifted toward culinary/cooking (especially baking/desserts) compared to Model A.

Reasoning:
- The logit-lens top tokens across the highest-norm cells are overwhelmingly culinary: “culinary,” “Food,” “Kitchen,” “Restaurant,” “Chef,” “Cook/Cooking,” “baking,” “Bake/Baked,” “Cake,” “Sweet,” “Café,” “Kitchen,” with professional qualifiers like “Professional,” “Advanced,” “Master,” “Institute.” Later layers (19–25) increasingly emphasize “Cake,” “baking,” “Baked,” “Bake,” “Chef,” etc., pointing specifically to baking/desserts.
- This pattern is consistent across positions p0–p4 and many layers (14–25), not a few idiosyncratic cells, suggesting a coherent domain bias rather than noise.
- The difference norm concentrates strongly in mid-to-late layers (peaking massively at layers 21–25, especially L25 p0), typical of higher-level semantic steering rather than surface-form quirks.

Caveat:
- Patchscope readouts aren’t provided here, so we can’t show direct continuations, but the consistent vocabulary direction strongly supports a culinary/baking domain specialization or preference in Model B.
```
