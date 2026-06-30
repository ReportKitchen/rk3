I’d design this as a **visual review → assertion capture → regression test** loop.

The user-facing button might say:

> **Lock this result**

But internally it should mean:

> “Create one or more assertions that future conversions must satisfy for this same source region.”

## The first thing the UI has to ask

“This needs to stay like it is” is too broad. The user should be able to choose what “like it is” means.

For example:

| User choice                 | What they are asserting                                                      |
| --------------------------- | ---------------------------------------------------------------------------- |
| Text is correct             | The extracted/cleaned text should remain the same                            |
| Structure is correct        | This should remain a heading, paragraph, list, table, caption, etc.          |
| Grouping is correct         | These pieces should stay together / not be split / not be merged             |
| Visual treatment is correct | Font size, weight, spacing, color, alignment, crop, etc. should remain close |
| Reading order is correct    | This should appear before/after nearby elements                              |
| Figure/table is correct     | Image/table extraction and caption association should remain stable          |
| Ignore this                 | This is decorative/noise and should stay excluded                            |

I would not make the reviewer configure every detail. Start with smart presets:

**“Lock text”**
Asserts normalized text content and maybe reading order.

**“Lock structure”**
Asserts element role, nesting, list/table structure, heading level, caption pairing.

**“Lock visual”**
Asserts rendered appearance of the selected region, with tolerances.

**“Lock all”**
Creates a bundle: text + structure + visual + source mapping.

## What gets recorded

Each assertion should record three things:

1. **How to find the thing again**
2. **What is expected**
3. **How strict the check should be**

The biggest design issue is the locator. A DOM selector alone is too fragile. A source PDF coordinate alone is not enough. You want a **multi-anchor locator**.

## Record source-side anchors

For the selected PDF/source region:

| Field                          | Why it matters                                            |
| ------------------------------ | --------------------------------------------------------- |
| PDF file hash                  | Ensures this applies to the exact source document/version |
| Page number                    | Primary source location                                   |
| Source bounding box            | “This thing on page 7 from x/y to x/y”                    |
| Glyph/char range if known      | Better than just coordinates                              |
| Raw extracted text             | Useful for re-finding after pipeline changes              |
| Normalized text fingerprint    | Useful for fuzzy matching                                 |
| Font IDs / font size / color   | Useful for visual and role matching                       |
| Nearby context text            | Helps relocate if bbox or segmentation changes            |
| Source screenshot crop         | Human/debug reference                                     |
| Source object IDs if available | Image object, font object, XObject, etc.                  |

The source screenshot crop is very important. It gives you a visual truth record even if all the extracted metadata changes.

## Record output-side anchors

For the current successful conversion:

| Field                              | Why it matters                                         |
| ---------------------------------- | ------------------------------------------------------ |
| Output node IDs                    | Fast path for same pipeline version                    |
| DOM path / semantic path           | Useful but fragile                                     |
| Generated HTML snippet             | Lets you inspect what was accepted                     |
| Normalized text                    | Main content assertion                                 |
| Role/classification                | h1, h2, paragraph, list item, table, figure, caption   |
| Parent/child relationships         | Prevents split/merge regressions                       |
| Rendered bbox                      | Visual comparison target                               |
| Computed CSS snapshot              | Font, size, line-height, weight, style, color, spacing |
| Rendered screenshot crop           | Baseline for visual regression                         |
| Pipeline version / commit / config | Explains why the assertion passed when created         |

I would give every meaningful output node a durable internal attribute, something like `data-rk-source-id` or `data-rk-block-id`, generated from source page + bbox + text fingerprint. Then assertions can attach to that, but still fall back to fuzzy matching.

## The assertion itself

A clean mental model:

| Piece      | Example                                                              |
| ---------- | -------------------------------------------------------------------- |
| Target     | “The selected source region on page 3”                               |
| Locator    | page + bbox + text fingerprint + screenshot crop                     |
| Invariant  | “Should be an h2 with text ‘Program Priorities’”                     |
| Normalizer | Collapse whitespace, repair line breaks, remove fake tracking spaces |
| Tolerance  | Heading level may be h2/h3? bbox within 8px? color within delta?     |
| Severity   | fail / warn / info                                                   |
| Scope      | document-only, fixture-library, or global regression candidate       |

That last point matters. Some assertions should only apply to one document. Others may become generalized tests later.

## Assertion types I’d support first

### 1. Text content assertion

Checks that the normalized output text still matches.

Good for:

* headings
* paragraphs
* captions
* pull quotes
* table cell text
* list items

Ignore benign changes like:

* line wrap differences
* multiple spaces
* soft hyphen removal
* curly vs straight quotes, optionally
* ligature normalization: `ﬁ` → `fi`
* hyphenation across line breaks
* fake tracking spaces: `R E P O R T` → `REPORT`

But preserve meaningful differences:

* missing words
* changed order
* merged headings
* dropped punctuation where it matters
* numbers changed
* captions attached to wrong figures

### 2. Role assertion

Checks that the item remains the same semantic type.

Examples:

| Selected thing    | Assertion                                       |
| ----------------- | ----------------------------------------------- |
| Big section title | Must remain heading                             |
| Heading level     | Should remain h2, or within allowed range h2–h3 |
| Bullet list       | Must remain unordered list                      |
| Numbered list     | Must remain ordered list                        |
| Caption           | Must remain caption, not body paragraph         |
| Table header      | Must remain table header cell                   |
| Sidebar text      | Must remain aside/callout                       |

This catches failures where the text is still present but the HTML becomes worse.

### 3. Grouping assertion

This may be one of the most useful for RK3.

Examples:

| Problem                              | Assertion                                |
| ------------------------------------ | ---------------------------------------- |
| Heading split into 3 separate blocks | These spans must merge into one heading  |
| Two columns interleaved              | These blocks must remain in this order   |
| Caption separated from figure        | Caption must stay associated with figure |
| List items flattened                 | These lines must remain one list         |
| Pull quote mixed with body           | Pull quote block must remain separate    |

A grouping assertion should record child source regions, expected output parent, and order.

### 4. Table assertion

Tables deserve their own assertion type.

Record:

* row count
* column count
* cell text
* header/body distinction
* colspan/rowspan if detected
* reading order
* whether it should be HTML table vs image fallback
* screenshot crop for visual comparison

The check should allow width changes and responsive layout changes, but not allow cell text to move to the wrong row/column.

### 5. Figure assertion

For a figure/image/chart:

Record:

* source page bbox
* extracted image/crop hash
* rendered image hash
* expected caption text
* caption proximity/association
* alt-text candidate, if generated
* crop boundaries
* whether vector/chart should be rasterized or reconstructed

Checks:

* figure still exists
* crop is visually similar
* caption still attached
* figure appears near expected text location/order
* no accidental inclusion of headers/footers/page furniture

Use perceptual hashing or SSIM-style visual comparison rather than exact image bytes, because compression and antialiasing can change.

### 6. Visual assertion

This is the trickiest but valuable.

Record both computed CSS and screenshot crop.

Computed style checks:

* font family or generated font token
* font size within tolerance
* font weight or exact embedded font face
* italic/normal
* color within tolerance
* letter spacing within tolerance
* line height within tolerance
* alignment
* margin/spacing range

Rendered visual checks:

* screenshot crop similarity
* bounding box size/position within tolerance
* text still appears as one line/multiline as expected
* no overlap/clipping
* background/callout box still present if relevant

For visual checks, do not compare full-page screenshots unless necessary. Compare the selected region plus a small amount of surrounding context.

## How the check system should run

For each assertion:

1. Load the source PDF and assertion record.
2. Run the current conversion pipeline.
3. Try to locate the target in the new output.
4. Normalize the relevant output.
5. Run assertion-specific checks.
6. Classify result as pass, warn, fail, or unresolved.
7. Show a diff/review panel when it fails.

The locator should use fallbacks:

| Locator tier     | Example                                           |
| ---------------- | ------------------------------------------------- |
| Exact output ID  | Same `data-rk-block-id` still exists              |
| Source mapping   | New output node maps to same PDF page/bbox        |
| Text fingerprint | Same normalized text appears nearby               |
| Visual region    | Same source screenshot/crop region maps to output |
| Fuzzy context    | Nearby heading/paragraph/caption matches          |

If the system cannot confidently locate the target, that should be a distinct result:

> **Unresolved: assertion target not found**

Not the same as:

> **Failed: target found but changed**

## How to ignore benign changes

This is where the assertion type matters. You avoid noisy failures by checking the thing the user actually cared about, not the whole HTML.

For text assertions, ignore:

* line wrapping
* extra whitespace
* fake tracking spaces
* ligature differences
* soft hyphens
* OCR-ish quote variations if allowed
* insignificant casing only when user marks it non-strict

For structure assertions, ignore:

* generated class names
* harmless wrapper elements
* ID changes
* CSS variable names
* DOM nesting that does not change semantic role

For visual assertions, ignore:

* subpixel differences
* antialiasing differences
* tiny color shifts
* small bbox drift
* browser rendering differences
* image recompression

For figure assertions, ignore:

* file name changes
* compression differences
* small crop expansion if content preserved
* responsive size changes

For table assertions, ignore:

* column width changes
* responsive wrapping
* `<thead>` vs first-row-header if semantically equivalent, depending on strictness
* cosmetic class changes

## The UI should make assertions inspectable

When the reviewer clicks “lock this,” show a small card:

**Locked: Section heading**
Text: `Building the Agricultural Bioeconomy`
Checks: text, heading role, visual style
Strictness: normal
Source: page 4, top third
Note: optional

And offer:

* make stricter
* make looser
* add note
* include surrounding block
* include only this text
* also lock visual appearance
* also lock relationship to figure/table

## Example presets

### “This heading is correct”

Creates assertions:

* normalized text equals expected text
* role is heading
* heading level remains h1/h2/h3 depending on chosen tolerance
* source region maps to one output heading block
* visual style remains close enough if visual lock enabled

### “This list is correct”

Creates assertions:

* same number of list items
* same item text after normalization
* ordered/unordered type preserved
* nesting preserved
* items remain grouped under one list parent
* preceding intro paragraph association optionally preserved

### “This chart extraction is correct”

Creates assertions:

* image/figure exists
* visual crop similar to baseline
* caption text matches
* caption remains attached
* figure appears in same reading-order neighborhood
* generated alt/caption metadata does not disappear, if applicable

### “This weird tracked headline is correct”

Creates assertions:

* source text normalized as `REPORT`
* output text must not contain `R E P O R T`
* CSS must include letter-spacing within tolerance
* rendered screenshot remains similar

That one is especially relevant to your current tracking issue.

## One subtle but important feature: assertions can become training examples

A document-specific assertion says:

> “For this document, this selected result must stay fixed.”

But after enough similar assertions, you can promote patterns:

> “All-caps single-letter spaced headings should collapse fake spaces and emit letter-spacing.”

So I’d tag each assertion with:

* issue category
* source pattern
* pipeline stage affected
* whether it is document-only or candidate-general
* reviewer confidence

That turns the review UI into both a QA tool and a rule/eval authoring interface.

## My suggested internal object model

Not code, just conceptually:

| Object           | Purpose                                           |
| ---------------- | ------------------------------------------------- |
| DocumentFixture  | The PDF and conversion settings being tested      |
| ReviewSelection  | What the user clicked/highlighted                 |
| SourceLocator    | How to find the source region again               |
| OutputLocator    | How it appeared in the accepted conversion        |
| Assertion        | The invariant being protected                     |
| Normalizer       | How to ignore benign differences                  |
| Comparator       | The actual check                                  |
| ToleranceProfile | Strict, normal, loose, visual-only, semantic-only |
| AssertionResult  | pass/warn/fail/unresolved with diffs              |

## The big rule

Do not lock the entire output by default.

Lock **specific invariants**:

* the text
* the role
* the grouping
* the order
* the visual crop
* the visual style
* the source/output relationship

That gives you high signal without turning every small improvement into a failing test.
