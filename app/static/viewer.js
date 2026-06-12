const ENGINE = "pdfium";
let docs = [];
let selected = null;

const $list = document.getElementById("doclist");
const $content = document.getElementById("content");
const $toolbar = document.getElementById("toolbar");
const $docname = document.getElementById("docname");
const $layer3 = document.getElementById("layer3");
const $showpdf = document.getElementById("showpdf");
const $sync = document.getElementById("syncscroll");

async function refresh() {
  docs = await (await fetch("/api/documents")).json();
  renderList();
  if (selected) renderRight();
}

function renderList() {
  $list.innerHTML = "";
  let folder = null;
  for (const d of docs) {
    if (d.folder !== folder) {
      folder = d.folder;
      const li = document.createElement("li");
      li.className = "folder";
      li.textContent = folder + "/";
      $list.appendChild(li);
    }
    const li = document.createElement("li");
    li.className = "doc" + (selected === d.slug ? " selected" : "");
    const badge = document.createElement("span");
    badge.className = "badge " + d.status;
    badge.textContent = {
      unconverted: "unconverted", in_progress: "in progress",
      done: "converted", failed: "failed",
    }[d.status] || d.status;
    const name = document.createElement("span");
    name.textContent = d.name;
    li.append(badge, name);
    li.onclick = () => { selected = d.slug; renderList(); renderRight(); };
    $list.appendChild(li);
  }
}

function renderRight() {
  const d = docs.find(x => x.slug === selected);
  if (!d) return;
  $toolbar.hidden = false;
  $docname.textContent = d.name;
  document.getElementById("layer3-wrap").style.visibility =
    d.status === "done" ? "visible" : "hidden";

  document.getElementById("showpdf-wrap").style.visibility =
    d.pages > 0 ? "visible" : "hidden";

  if (d.status === "done") {
    $content.innerHTML = "";
    const split = document.createElement("div");
    split.className = "split";
    const iframe = document.createElement("iframe");
    iframe.src = `/output/${ENGINE}/${d.slug}/index.html`;
    const pdfPane = buildPdfPane(d);
    pdfPane.hidden = !$showpdf.checked;
    split.append(iframe, pdfPane);
    $content.appendChild(split);
    iframe.onload = () => { applyLayer3(iframe); setupSync(iframe, pdfPane); };
  } else if (d.status === "in_progress") {
    $content.innerHTML = `<div class="pane"><p>Conversion in progress…</p>
      <p class="hint">No live progress in v1 — use Refresh to check.</p></div>`;
  } else {
    const failed = d.status === "failed";
    $content.innerHTML = `<div class="pane">
      ${failed ? `<p><strong>Conversion failed.</strong></p>
                  <pre class="error">${escapeHtml(d.error || "unknown error")}</pre>` : ""}
      <button class="action" id="convert">${failed ? "Retry conversion" : "Convert"}</button>
    </div>`;
    document.getElementById("convert").onclick = async () => {
      await fetch(`/api/convert/${d.slug}` + (failed ? "?force=true" : ""), { method: "POST" });
      await refresh();
    };
    // failed docs may still have page renders (e.g. the scanned-PDF bail-out):
    // show the original pages so there is something to look at
    if (d.pages > 0 && $showpdf.checked) {
      const pdfPane = buildPdfPane(d);
      pdfPane.classList.add("solo");
      $content.appendChild(pdfPane);
    }
  }
}

function buildPdfPane(d) {
  const pane = document.createElement("div");
  pane.className = "pdfpane";
  for (let p = 1; p <= d.pages; p++) {
    const img = document.createElement("img");
    img.src = `/output/${ENGINE}/${d.slug}/pages/page-${String(p).padStart(4, "0")}.png`;
    img.dataset.page = p;
    pane.appendChild(img);
  }
  return pane;
}

// Smooth sync scroll. Every converted element carries data-page (source page)
// and data-yf (fractional vertical position on that page), so each element is
// an anchor pairing an HTML offset with a position in the page-image stack.
// Scrolling one pane interpolates between the bracketing anchors to position
// the other.
function setupSync(iframe, pdfPane) {
  const win = iframe.contentWindow;
  const doc = iframe.contentDocument;
  if (!win || !doc) return;

  let anchors = null;
  let dirty = true;
  for (const img of pdfPane.children) {
    img.addEventListener("load", () => { dirty = true; });
  }

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
    let maxPy = -Infinity; // enforce monotonic so interpolation never reverses
    for (const a of list) { maxPy = Math.max(maxPy, a.py); a.py = maxPy; }
    return list;
  }

  function getAnchors() {
    if (dirty || !anchors) { anchors = buildAnchors(); dirty = false; }
    return anchors;
  }

  // piecewise-linear map of y between the two anchor coordinate spaces
  function project(y, from, to) {
    const list = getAnchors();
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

  win.addEventListener("scroll", () => {
    if (!$sync.checked || pdfPane.hidden || performance.now() < lockUntil) return;
    const target = Math.round(project(win.scrollY, "hy", "py"));
    if (Math.abs(pdfPane.scrollTop - target) > 2) {
      lockUntil = performance.now() + 150;
      pdfPane.scrollTop = target;
    }
  });

  pdfPane.addEventListener("scroll", () => {
    if (!$sync.checked || performance.now() < lockUntil) return;
    const target = Math.round(project(pdfPane.scrollTop, "py", "hy"));
    if (Math.abs(win.scrollY - target) > 2) {
      lockUntil = performance.now() + 150;
      win.scrollTo(0, target);
    }
  });
}

function applyLayer3(iframe) {
  const link = iframe.contentDocument?.getElementById("css-original");
  if (link) link.disabled = !$layer3.checked;
}

$layer3.onchange = () => {
  const iframe = $content.querySelector("iframe");
  if (iframe) applyLayer3(iframe);
};

$showpdf.onchange = () => {
  const pane = $content.querySelector(".pdfpane");
  if (pane) pane.hidden = !$showpdf.checked;
  else renderRight(); // failed-doc solo pane is built on demand
};

document.getElementById("refresh").onclick = refresh;
refresh();
