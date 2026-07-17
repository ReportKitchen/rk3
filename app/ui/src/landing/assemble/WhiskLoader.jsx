import React, { useEffect, useState } from "react";

// Report Kitchen whisk — the smoother pure-CSS loader (from
// sources/docs/assets/whisk-loader.html): a fixed-tilt whisk whose direction
// precesses via an animated @property angle, so it twirls in real 3D while always
// facing you. `captions` cycles through phrases every few seconds; `caption` is a
// single fixed label.
const WhiskSvg = () => (
  <svg className="asm-whisk-svg" viewBox="0 0 10.2 42.2" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
    {/* translate/rotate maps the original horizontal whisk to vertical */}
    <g transform="translate(10.2,0) rotate(90)" fill="var(--rk-tomato, #D72E2B)">
      <path d="M16.1,4.7c0-1-0.8-1.8-1.7-1.8L1.8,2.7C0.8,2.7,0,3.5,0,4.4c0,1,0.8,1.8,1.7,1.8l12.6,0.2 C15.3,6.5,16,5.7,16.1,4.7z M0.8,4.5c0-0.4,0.4-0.8,0.8-0.8c0.4,0,0.8,0.4,0.8,0.8c0,0.4-0.4,0.8-0.8,0.8C1.2,5.2,0.8,4.9,0.8,4.5z" />
      <path d="M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2C20.8,4.4,34.5,0,37.2,0c2.8,0,5,2.4,5,5.2 c0,2.8-2.4,5.1-5.2,5l0,0c-2.7,0-16.2-4.9-16.8-5.1C20.1,5,20,4.9,20,4.8z M41.7,5.1c0-2.5-2-4.5-4.5-4.6 c-2.3,0-13.2,3.4-16.1,4.3c2.9,1,13.7,4.8,16,4.9C39.5,9.7,41.6,7.7,41.7,5.1C41.7,5.1,41.7,5.1,41.7,5.1z M37,9.9L37,9.9L37,9.9z" />
      <path d="M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2c0.6-0.1,14.3-2.8,16.9-2.8c2.8,0,5,1.6,5,3.4 c0,0,0,0,0,0c0,0.9-0.6,1.8-1.6,2.4c-1,0.6-2.2,0.9-3.6,0.9c-2.7,0-16.2-3.3-16.8-3.4C20.1,5,20,4.9,20,4.8z M41.7,5.1 c0-1.5-2-2.8-4.5-2.9c-2.2,0-12.2,1.9-15.7,2.6C24.8,5.6,34.8,7.9,37,7.9c1.2,0,2.4-0.3,3.3-0.8C41.2,6.6,41.6,5.9,41.7,5.1 C41.7,5.2,41.7,5.2,41.7,5.1z" />
      <path d="M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.3c0.6,0,14.2-1,16.9-0.9c1.3,0,2.5,0.2,3.5,0.4 c1.1,0.3,1.6,0.7,1.6,1.1c0,1-2.7,1.4-5.1,1.4l0,0c-2.7,0-16.2-1.4-16.8-1.5C20.1,5,20,4.9,20,4.8z M41.7,5.2 c0-0.1-0.2-0.4-1.2-0.6c-0.9-0.2-2.1-0.4-3.4-0.4c-1.9,0-9.5,0.4-13.8,0.7C27.6,5.3,35.2,6,37.1,6C40,6.1,41.6,5.5,41.7,5.2 L41.7,5.2z" />
      <rect x="18" y="2.3" width="1.9" height="4.9" transform="matrix(1.756758e-02 -0.9998 0.9998 1.756758e-02 13.783 23.5703)" />
    </g>
  </svg>
);

export default function WhiskLoader({ size = 150, caption, captions }) {
  const list = captions && captions.length ? captions : (caption ? [caption] : []);
  const [i, setI] = useState(0);
  useEffect(() => {
    if (list.length <= 1) return undefined;
    const id = setInterval(() => setI((n) => n + 1), 2600);
    return () => clearInterval(id);
  }, [list.length]);
  const cap = list.length ? list[i % list.length] : null;
  return (
    <div className="asm-whisk" style={{ "--whisk-h": `${size}px` }}>
      <div className="asm-whisk-scene"><div className="asm-whisk-spin"><WhiskSvg /></div></div>
      <div className="asm-whisk-shadow" />
      {cap && <div className="asm-whisk-cap">{cap}<span className="asm-whisk-dots" /></div>}
    </div>
  );
}
