import JSZip from "jszip";

// A minimal, real .docx (OOXML is just a zip of XML parts — we already ship
// JSZip, so no new dependency): title + cadence intro + Week N / post pairs.
// Opens cleanly in Word, Google Docs, and LibreOffice. All display strings come
// from the caller (registry copy) — this is a pure builder.

const esc = (s) => String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");

// w:sz is half-points (22 = 11pt); w:spacing after is twentieths of a point
const para = (text, { bold = false, size = 22, after = 160 } = {}) =>
  `<w:p><w:pPr><w:spacing w:after="${after}"/></w:pPr><w:r><w:rPr>` +
  `${bold ? "<w:b/>" : ""}<w:sz w:val="${size}"/><w:szCs w:val="${size}"/></w:rPr>` +
  `<w:t xml:space="preserve">${esc(text)}</w:t></w:r></w:p>`;

const CONTENT_TYPES = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>`;

const RELS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`;

// title/intro/weekLabel(n)/posts — returns a Promise<Blob> of the .docx
export function buildSocialDocx({ title, intro, weekLabel, posts }) {
  const body = [
    para(title, { bold: true, size: 32, after: 240 }),
    para(intro, { after: 320 }),
    ...posts.flatMap((text, i) => [
      para(weekLabel(i + 1), { bold: true, size: 24, after: 80 }),
      para(text, { after: 320 }),
    ]),
  ].join("");
  const doc = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>${body}<w:sectPr/></w:body></w:document>`;

  const zip = new JSZip();
  zip.file("[Content_Types].xml", CONTENT_TYPES);
  zip.folder("_rels").file(".rels", RELS);
  zip.folder("word").file("document.xml", doc);
  return zip.generateAsync({
    type: "blob",
    mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
}
