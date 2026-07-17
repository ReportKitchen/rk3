import React, { useEffect, useRef } from "react";

// Report Kitchen whisk — a pseudo-3D tumbling loader, ported from
// sources/docs/assets/report-kitchen-whisk-loader.html. The inner group's affine
// transform is recomputed each frame from a rotating axis, so the exact-logo
// whisk appears to whisk in 3D.
export default function WhiskLoader({ size = 120, caption }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const pivot = { x: 120, y: 100 };
    const focal = 390, camera = 490, cone = Math.PI / 6.6, speed = (2 * Math.PI) / 1220, mult = 3.8;
    const vec = (x, y, z) => ({ x, y, z });
    const cross = (a, b) => vec(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
    const len = (v) => Math.hypot(v.x, v.y, v.z);
    const norm = (v) => { const l = len(v) || 1; return vec(v.x / l, v.y / l, v.z / l); };
    const project = (p) => { const s = focal / (camera - p.z); return { x: pivot.x + p.x * s, y: pivot.y + p.y * s }; };
    const update = (t) => {
      const theta = t * speed;
      const axis = norm(vec(Math.sin(cone) * Math.cos(theta), Math.cos(cone), Math.sin(cone) * Math.sin(theta)));
      const refv = Math.abs(axis.z) < 0.92 ? vec(0, 0, 1) : vec(1, 0, 0);
      const side = norm(cross(refv, axis));
      const O = project(vec(0, 0, 0)), X = project(side), Y = project(axis);
      const a = (X.x - O.x) * mult, b = (X.y - O.y) * mult, c = (Y.x - O.x) * mult, d = (Y.y - O.y) * mult;
      el.setAttribute("transform", `matrix(${a.toFixed(5)} ${b.toFixed(5)} ${c.toFixed(5)} ${d.toFixed(5)} ${O.x.toFixed(5)} ${O.y.toFixed(5)})`);
      raf = requestAnimationFrame(update);
    };
    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, []);
  return (
    <div className="asm-whisk">
      <svg width={size} height={size} viewBox="0 0 240 240" style={{ overflow: "visible" }} aria-label="Loading" role="img">
        <g ref={ref}>
          <g transform="rotate(90) translate(-20.1 -4.75)" fill="var(--rk-tomato, #D72E2B)">
            <path d="M16.1,4.7c0-1-0.8-1.8-1.7-1.8L1.8,2.7C0.8,2.7,0,3.5,0,4.4c0,1,0.8,1.8,1.7,1.8l12.6,0.2 C15.3,6.5,16,5.7,16.1,4.7z M0.8,4.5c0-0.4,0.4-0.8,0.8-0.8c0.4,0,0.8,0.4,0.8,0.8c0,0.4-0.4,0.8-0.8,0.8C1.2,5.2,0.8,4.9,0.8,4.5z" />
            <path d="M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2C20.8,4.4,34.5,0,37.2,0c2.8,0,5,2.4,5,5.2 c0,2.8-2.4,5.1-5.2,5l0,0c-2.7,0-16.2-4.9-16.8-5.1C20.1,5,20,4.9,20,4.8z M41.7,5.1c0-2.5-2-4.5-4.5-4.6 c-2.3,0-13.2,3.4-16.1,4.3c2.9,1,13.7,4.8,16,4.9C39.5,9.7,41.6,7.7,41.7,5.1C41.7,5.1,41.7,5.1,41.7,5.1z M37,9.9L37,9.9L37,9.9z" />
            <path d="M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.2c0.6-0.1,14.3-2.8,16.9-2.8c2.8,0,5,1.6,5,3.4 c0,0,0,0,0,0c0,0.9-0.6,1.8-1.6,2.4c-1,0.6-2.2,0.9-3.6,0.9c-2.7,0-16.2-3.3-16.8-3.4C20.1,5,20,4.9,20,4.8z M41.7,5.1 c0-1.5-2-2.8-4.5-2.9c-2.2,0-12.2,1.9-15.7,2.6C24.8,5.6,34.8,7.9,37,7.9c1.2,0,2.4-0.3,3.3-0.8C41.2,6.6,41.6,5.9,41.7,5.1 C41.7,5.2,41.7,5.2,41.7,5.1z" />
            <path d="M20,4.8C20,4.8,20,4.8,20,4.8c0-0.1,0.1-0.2,0.2-0.3c0.6,0,14.2-1,16.9-0.9c1.3,0,2.5,0.2,3.5,0.4 c1.1,0.3,1.6,0.7,1.6,1.1c0,1-2.7,1.4-5.1,1.4l0,0c-2.7,0-16.2-1.4-16.8-1.5C20.1,5,20,4.9,20,4.8z M41.7,5.2 c0-0.1-0.2-0.4-1.2-0.6c-0.9-0.2-2.1-0.4-3.4-0.4c-1.9,0-9.5,0.4-13.8,0.7C27.6,5.3,35.2,6,37.1,6C40,6.1,41.6,5.5,41.7,5.2L41.7,5.2z" />
            <rect x="18" y="2.3" width="1.9" height="4.9" transform="matrix(1.756758e-02 -0.9998 0.9998 1.756758e-02 13.783 23.5703)" />
          </g>
        </g>
      </svg>
      {caption && (
        <div className="asm-whisk-cap">
          {caption}
          <span className="asm-whisk-dots"><span /><span /><span /></span>
        </div>
      )}
    </div>
  );
}
