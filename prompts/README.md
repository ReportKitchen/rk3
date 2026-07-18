# prompts/

Every LLM prompt and instruction the RK3 engine sends to a model lives here as an
editable file — one place to review and tune model behavior **without tracing
through code**.

These are load-bearing **code assets**, not documentation: the engine reads them
at runtime via `rk3.prompts.load_prompt(name)`. They ship with the codebase (this
directory must be deployed alongside `rk3/`). This is deliberately **not** under
`docs/`, which is not deployed.

Prompts are read fresh on every model call, so editing a file here takes effect on
the next call — no restart needed.

## Files

| File | Used by | Purpose |
|---|---|---|
| `vision-qa.system.md` | `rk3.visionqa._system()` | The vision QA reviewer's system prompt — compares original vs our render, flags discrepancies (incl. duplicated-content and wrong-fill hunts), classifies kind/severity. |
| `vision-qa.rubric.md` | `rk3.visionqa._system()` | The DISTILLED conversion rubric appended to the QA system prompt — resolved PRESERVE/TRANSFORM/ERROR rules only. Distilled from the design doc `sources/docs/conversion-rubric.md` (which stays in docs/, is NOT a prompt, and carries OPEN questions that confused the scanner when fed raw). |
| `vision-prescribe.system.md` | `rk3.visionqa.prescribe()` | The prescriber's system prompt — turns a scanned discrepancy into the minimal set of per-document override levers. |
| `landing-copy.system.md` | `rk3.landing.ai` | Landing Page Maker: writes concise landing-page copy from the document (no invented facts). |
| `landing-analyze.system.md` | `rk3.landing.ai` | Landing Page Maker: identifies which existing section is the document's intro/executive summary. |
| `landing-findings.system.md` | `rk3.landing.ai` | Landing Page Maker: extracts quantified key findings from the document. |
| `social-openai-reformat.md` | `rk3.social_post` | Direct GPT Image edit: recompose the vertical cover as a horizontal social post. |
| `social-gemini-reformat.md` | `rk3.social_post` | Direct Gemini image edit: one-shot recompose of the cover as a 16:9 social post. |
| `social-cover.user.md` | `rk3.social_post` | Shared image-attached user instruction for the OpenAI and Claude analysis paths. |
| `social-claude-reformat.system.md` | `rk3.social_post` | Claude art direction passed to GPT Image for the Claude-directed reformat path. |
| `social-openai-rebuild.system.md` | `rk3.social_post` | OpenAI vision-to-SVG reconstruction prompt. |
| `social-claude-rebuild.system.md` | `rk3.social_post` | Claude vision-to-SVG reconstruction prompt. |
| `patterns/vet-candidates.system.md` | `patterns.vet` | Pattern worktrack: asks an LLM to review deterministic pattern candidates and explain accepts/rejects/wrong-type calls. |
| `patterns/scan-document.system.md` | `patterns.scan` | Pattern worktrack: asks an LLM to independently scan document excerpts for Landing Page-relevant signals: statistics, impact statements, funding events, quotations, key findings, and recommendations. |

To add a prompt: drop a file here and load it with `load_prompt("<name>")`.
