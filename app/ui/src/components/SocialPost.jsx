import React, { useCallback, useEffect, useRef, useState } from "react";
import { generateSocialPost, getSocialPost } from "../api.js";
import { reportError } from "../errorBus.js";

const ROWS = [
  {
    id: "reformat",
    cells: [
      { mode: "openai-reformat", label: "Reformat image", button: "Run OpenAI reformat",
        note: "OpenAI sends the cover directly to GPT Image for a horizontal edit." },
      { mode: "claude-reformat", label: "Reformat image", button: "Run Claude → OpenAI",
        note: "Claude analyzes the cover and writes art direction; GPT Image performs the edit." },
      { mode: "gemini-reformat", label: "Reformat image", button: "Run Gemini one-shot",
        note: "Gemini receives the cover and directly generates the horizontal edit in one call." },
    ],
  },
  {
    id: "rebuild",
    cells: [
      { mode: "openai-rebuild", label: "Rebuild in SVG", button: "Run OpenAI rebuild",
        note: "OpenAI analyzes the cover and reconstructs it as SVG; RK3 rasterizes it." },
      { mode: "claude-rebuild", label: "Rebuild in SVG", button: "Run Claude rebuild",
        note: "Claude analyzes the cover and reconstructs it as SVG; RK3 rasterizes it." },
      null,
    ],
  },
];

const EMPTY = { modes: {} };

const money = (value) => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 4,
}).format(value);

function CostSummary({ result }) {
  const usage = result?.usage;
  if (!usage?.calls?.length) {
    return result?.url ? <div className="social-cost unavailable">Cost unavailable for this earlier run.</div> : null;
  }
  const total = usage.totalCostUsd;
  return (
    <div className="social-cost">
      <div className="social-cost-total">
        {usage.costComplete ? "Estimated API cost" : "Known API cost"}
        <strong>{total == null ? " unavailable" : ` ${money(total)}`}</strong>
      </div>
      <div className="social-cost-calls">
        {usage.calls.map((call, index) => (
          <span key={`${call.provider}-${index}`}>
            {call.provider === "anthropic" ? "Claude" : call.provider === "google" ? "Gemini" : call.kind === "image_edit" ? "GPT Image" : "OpenAI"}
            {call.costUsd == null ? " — unknown" : ` — ${money(call.costUsd)}`}
            {` · ${call.inputTokens.toLocaleString()} in / ${call.outputTokens.toLocaleString()} out`}
          </span>
        ))}
      </div>
    </div>
  );
}

function ResultCell({ slug, mode, label, note, button, result, onStarted }) {
  const busy = result?.status === "in_progress";
  const run = async () => {
    try {
      const data = await generateSocialPost(slug, mode);
      onStarted(data);
    } catch (error) {
      reportError(`social post: ${mode}`, error);
    }
  };

  return (
    <td className="social-cell">
      <div className="social-cell-method">
        <strong>{label}</strong>
        <span>{note}</span>
      </div>
      <button className="social-generate" type="button" disabled={busy} onClick={run}>
        {busy ? "Generating…" : button}
      </button>
      <div className="social-result" aria-live="polite">
        {result?.url && <img src={result.url} alt={`${mode} social-post result`} />}
        {busy && <div className="social-working">This may take a couple of minutes.</div>}
      </div>
      {result?.error && <div className="social-error">{result.error}</div>}
      <CostSummary result={result} />
    </td>
  );
}

export default function SocialPost({ doc }) {
  const [data, setData] = useState(EMPTY);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const next = await getSocialPost(doc.slug);
      if (mounted.current) setData(next);
      return next;
    } catch (error) {
      reportError("load social-post results", error);
      return null;
    }
  }, [doc.slug]);

  useEffect(() => {
    mounted.current = true;
    refresh();
    return () => { mounted.current = false; };
  }, [refresh]);

  const running = Object.values(data.modes || {}).some((m) => m.status === "in_progress");
  useEffect(() => {
    if (!running) return undefined;
    const timer = window.setInterval(refresh, 1500);
    return () => window.clearInterval(timer);
  }, [running, refresh]);

  return (
    <div className="social-post-pane">
      <div className="social-post-intro">
        <h2>Social Post</h2>
        <p>Five cover-to-social experiments. Every click regenerates that cell and replaces its saved image only after the new result succeeds.</p>
      </div>
      {data.cover && (
        <figure className="social-cover-reference">
          <img src={data.cover} alt="Original PDF cover" />
          <figcaption>Original cover</figcaption>
        </figure>
      )}
      <div className="social-table-wrap">
        <table className="social-table">
          <thead>
            <tr>
              <th scope="col">OpenAI pathway</th>
              <th scope="col">Claude-directed pathway</th>
              <th scope="col">Gemini one-shot</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.id}>
                {row.cells.map((cell, index) => cell ? (
                  <ResultCell
                    key={cell.mode}
                    slug={doc.slug}
                    mode={cell.mode}
                    label={cell.label}
                    note={cell.note}
                    button={cell.button}
                    result={data.modes?.[cell.mode]}
                    onStarted={setData}
                  />
                ) : <td className="social-cell social-cell-empty" key={`${row.id}-${index}`} />)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
