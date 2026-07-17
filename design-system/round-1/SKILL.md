---
name: report-kitchen-design
description: Use this skill to generate well-branded interfaces and assets for Report Kitchen, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick reference
- **Brand:** Report Kitchen — turns dense PDFs into interactive, accessible, responsive websites. Audience: nonprofit / foundation / higher-ed communications pros. Voice: warm, witty, culinary metaphor with real substance. No emoji.
- **Colors:** Tomato #D72E2C (primary/brand), Macaroni #F2BB2E (bright accent), Blueberry Muffin #7683A2 (support), Rhino #303D61 (ink/dark), Steel #DDDDDD (light neutral). Warm paper #FBF7F0 page ground. Full ramps + semantic aliases in `tokens/colors.css`.
- **Type:** Bricolage Grotesque (headings) + Mulish (body). Kano = logo only. *(Both site fonts are proposals replacing Lato — confirm with client.)*
- **Look:** NO photography — flat color blocks, confident type, Lucide line icons. Whisk mark only in the logo lockup and faint footer accents (never a background pattern).
- **Global CSS:** link `styles.css`. Components: `window.ReportKitchenDesignSystem_07c3a7` after loading `_ds_bundle.js`.

See `readme.md` for full CONTENT FUNDAMENTALS, VISUAL FOUNDATIONS, and ICONOGRAPHY. Components live in `components/`, the site recreation in `ui_kits/website/`.
