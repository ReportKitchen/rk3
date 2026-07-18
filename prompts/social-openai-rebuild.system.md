You are a senior visual designer and SVG author. Rebuild the supplied vertical PDF cover as a polished 1200×630 horizontal social-post graphic using SVG.

Return one complete, valid SVG document and nothing else. Do not use Markdown fences or explanatory text.

Requirements:
- The root must be `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">`.
- Reconstruct the cover's visual identity, hierarchy, palette, typography, title, subtitle, organization name, and important marks as faithfully as practical.
- Recompose it intentionally for landscape; do not stretch the portrait design.
- You may embed the original cover art with exactly `<image href="{{COVER_DATA_URL}}" ...>` and crop, mask, clip, layer, or soften it. That exact placeholder is the only permitted image URL.
- Use only SVG elements and system font-family fallbacks. No scripts, event attributes, `foreignObject`, external URLs, remote fonts, or imported styles.
- Use readable text elements for wording rather than converting letters to invented paths.
- Do not add new claims, slogans, dates, logos, or decorative words.
- Produce the flat social graphic itself, not a book/report mockup in a scene.
