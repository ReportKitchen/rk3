import React from "react";
import {
  EditorProvider, Editor, Toolbar,
  BtnBold, BtnItalic, BtnBulletList, BtnLink, createButton,
} from "react-simple-wysiwyg";

// Heading button: toggles the current block between <h3> and plain text. The
// library's built-ins cover bold/italic/list/link; formatBlock needs a value,
// so it's a custom button.
const BtnHeading = createButton("Heading", <b style={{ fontSize: 15 }}>H</b>, () => {
  const cur = (document.queryCommandValue("formatBlock") || "").toLowerCase();
  document.execCommand("formatBlock", false, cur === "h3" ? "div" : "h3");
});

// One small rich-text field (bold / italic / heading / bullets / links) shared
// by every prose block. Stores and emits an HTML string; the blocks render it
// with dangerouslySetInnerHTML, so the editor, preview and export stay in sync.
export function RichText({ value, onChange, placeholder }) {
  // Enter should start a <p>, not the browser-default <div>, so the rendered
  // output matches the .lp-rich paragraph styling
  React.useEffect(() => {
    try { document.execCommand("defaultParagraphSeparator", false, "p"); } catch { /* older browsers */ }
  }, []);
  return (
    <div className="lp-rte">
      <EditorProvider>
        <Editor
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        >
          <Toolbar>
            <BtnBold />
            <BtnItalic />
            <BtnHeading />
            <BtnBulletList />
            <BtnLink />
          </Toolbar>
        </Editor>
      </EditorProvider>
    </div>
  );
}
