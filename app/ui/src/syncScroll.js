// Smooth sync scroll between the converted-HTML iframe and the page-image
// pane. Anchors pair each element's HTML offset (via offsetTop) with its
// position in the image stack (via data-page + data-yf emitted by render).
// Piecewise-linear interpolation between bracketing anchors; a short lock
// prevents the two scroll handlers from feeding back into each other.
export function setupSync(win, doc, pdfPane, isEnabled) {
  let anchors = null;
  let dirty = true;

  const markDirty = () => { dirty = true; };
  for (const img of pdfPane.children) img.addEventListener("load", markDirty);

  function buildAnchors() {
    const list = [];
    for (const el of doc.querySelectorAll("[data-page][data-yf]")) {
      const p = parseInt(el.dataset.page, 10);
      const yf = parseFloat(el.dataset.yf);
      const img = pdfPane.querySelector(`img[data-page="${p}"]`);
      if (!p || !img || isNaN(yf)) continue;
      list.push({ hy: el.offsetTop, py: img.offsetTop + yf * img.clientHeight });
    }
    list.sort((a, b) => a.hy - b.hy);
    let maxPy = -Infinity;
    for (const a of list) { maxPy = Math.max(maxPy, a.py); a.py = maxPy; }
    return list;
  }

  function project(y, from, to) {
    if (dirty || !anchors) { anchors = buildAnchors(); dirty = false; }
    const list = anchors;
    if (!list.length) return 0;
    if (y <= list[0][from]) return list[0][to] - (list[0][from] - y);
    let prev = list[0];
    for (const a of list) {
      if (a[from] >= y) {
        const span = a[from] - prev[from];
        const t = span > 0 ? (y - prev[from]) / span : 0;
        return prev[to] + t * (a[to] - prev[to]);
      }
      prev = a;
    }
    return prev[to] + (y - prev[from]);
  }

  let lockUntil = 0;

  const onWinScroll = () => {
    if (!isEnabled() || performance.now() < lockUntil) return;
    const target = Math.round(project(win.scrollY, "hy", "py"));
    if (Math.abs(pdfPane.scrollTop - target) > 2) {
      lockUntil = performance.now() + 150;
      pdfPane.scrollTop = target;
    }
  };

  const onPdfScroll = () => {
    if (!isEnabled() || performance.now() < lockUntil) return;
    const target = Math.round(project(pdfPane.scrollTop, "py", "hy"));
    if (Math.abs(win.scrollY - target) > 2) {
      lockUntil = performance.now() + 150;
      win.scrollTo(0, target);
    }
  };

  win.addEventListener("scroll", onWinScroll);
  pdfPane.addEventListener("scroll", onPdfScroll);
  return () => {
    win.removeEventListener("scroll", onWinScroll);
    pdfPane.removeEventListener("scroll", onPdfScroll);
    for (const img of pdfPane.children) img.removeEventListener("load", markDirty);
  };
}
