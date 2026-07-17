import React from "react";

// Oversized opening-quote glyphs for the pullquote treatments (design-system/
// quotes 5a–5f). Baked from several fonts as SVG paths (docs/assets/*.svg) so the
// look never depends on a web font. fill=currentColor, so the glyph takes
// --lp-accent. Sized by height (em); the viewBox carries the aspect.
const GLYPHS = {
  // rounded, warm/bookish (Agbalumo)
  rounded: { vb: "0 23.25 21.4 15.5", d: "M21.30 23.25L21.40 23.70Q18.60 25.50 18.60 28.85Q18.60 29.95 18.90 31.40Q19 31.95 19.08 32.50Q19.15 33.05 19.15 33.60Q19.15 36.15 17.80 37.45Q16.45 38.75 14.70 38.75Q12.70 38.75 11.60 37.27Q10.50 35.80 10.50 33.65Q10.50 32 11.22 30.15Q11.95 28.30 13.40 26.75Q15.20 24.85 17.33 24.05Q19.45 23.25 21.30 23.25M10.80 23.25L10.90 23.70Q8.10 25.50 8.10 28.85Q8.10 29.95 8.40 31.40Q8.50 31.95 8.58 32.50Q8.65 33.05 8.65 33.60Q8.65 36.15 7.30 37.45Q5.95 38.75 4.20 38.75Q2.20 38.75 1.10 37.27Q0 35.80 0 33.65Q0 32 0.72 30.15Q1.45 28.30 2.90 26.75Q4.70 24.85 6.82 24.05Q8.95 23.25 10.80 23.25Z" },
  // chunky sans, poster-like (Archivo Black)
  chunky: { vb: "0 9.5 20.75 17.85", d: "M9.30 18.60L9.30 27.35L0 27.35L0 19.10L4.55 9.50L9.30 9.50L5.75 18.60L9.30 18.60M20.75 18.60L20.75 27.35L11.45 27.35L11.45 19.10L16 9.50L20.75 9.50L17.20 18.60L20.75 18.60Z" },
  // serif (Lora)
  serif: { vb: "0 12.3 15.1 14.0", d: "M3.70 12.30L5.05 13.30Q4.50 14.00 3.90 15.30Q3.30 16.60 2.95 18.15Q2.60 19.70 2.75 21.25Q3.10 21.10 3.40 21.02Q3.70 20.95 4 20.95Q5 20.95 5.65 21.65Q6.30 22.35 6.30 23.40Q6.30 24.80 5.50 25.55Q4.70 26.30 3.55 26.30Q1.85 26.30 0.92 24.97Q0 23.65 0 21.75Q0 20.45 0.48 18.67Q0.95 16.90 1.77 15.15Q2.60 13.40 3.70 12.30M12.50 12.30L13.85 13.30Q13.30 14.00 12.70 15.30Q12.10 16.60 11.75 18.15Q11.40 19.70 11.55 21.25Q11.90 21.10 12.20 21.02Q12.50 20.95 12.80 20.95Q13.80 20.95 14.45 21.65Q15.10 22.35 15.10 23.40Q15.10 24.80 14.30 25.55Q13.50 26.30 12.35 26.30Q10.65 26.30 9.72 24.97Q8.80 23.65 8.80 21.75Q8.80 20.45 9.28 18.67Q9.75 16.90 10.57 15.15Q11.40 13.40 12.50 12.30Z" },
};

export function QuoteGlyph({ font = "rounded", size = "1em", className }) {
  const g = GLYPHS[font] || GLYPHS.rounded;
  return (
    <svg viewBox={g.vb} fill="currentColor" aria-hidden="true" className={className}
      style={{ height: size, width: "auto", display: "block" }}>
      <path d={g.d} />
    </svg>
  );
}
