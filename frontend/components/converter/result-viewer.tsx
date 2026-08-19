import { AlertTriangle, Check, Clipboard, Download, FileText, Package, RotateCcw } from "lucide-react";
import { memo, useState } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { resultUrl } from "@/lib/api";
import type { ConversionResult } from "@/lib/types";

export function ResultViewer({ result, apiUrl, onReset }: { result: ConversionResult; apiUrl: string; onReset: () => void }) {
  const [tab, setTab] = useState<"preview" | "markdown">("preview");
  const [copied, setCopied] = useState(false);
  const copy = async () => { await navigator.clipboard.writeText(result.markdown); setCopied(true); window.setTimeout(() => setCopied(false), 1800); };
  const assetBase = `${apiUrl.replace(/\/+$/, "")}/api/results/${result.result_id}/`;
  return (
    <section className="result-card" aria-labelledby="result-title">
      <div className="result-topbar">
        <div><span className="eyebrow success"><Check size={14} /> Conversion complete</span><h2 id="result-title">{result.metadata.output_filename}</h2></div>
        <div className="download-group">
          <a className="button primary" href={resultUrl(apiUrl, result.markdown_url)} download><FileText size={16} /> Download Markdown</a>
          {(result.metadata.figures > 0 || result.metadata.table_images > 0) && <a className="button secondary" href={resultUrl(apiUrl, result.package_url)} download><Package size={16} /> Download Package</a>}
          <button className="button tertiary" onClick={copy}>{copied ? <Check size={16} /> : <Clipboard size={16} />}{copied ? "Copied" : "Copy Markdown"}</button>
        </div>
      </div>
      <dl className="metadata">
        <div><dt>Engine</dt><dd>{engineLabel(result.metadata.engine)}</dd></div>
        {result.metadata.pages !== null && <div><dt>Pages</dt><dd>{result.metadata.pages}</dd></div>}
        <div><dt>Processing time</dt><dd>{result.metadata.processing_seconds.toFixed(1)}s</dd></div>
        <div><dt>Figures</dt><dd>{result.metadata.figures}</dd></div>
        <div><dt>Table images</dt><dd>{result.metadata.table_images}</dd></div>
      </dl>
      <p className="engine-reason">{result.metadata.engine_reason}{result.metadata.cache_hit ? " Cached result." : ""}</p>
      {result.metadata.warnings.length > 0 && <details className="result-warnings"><summary><AlertTriangle size={15} /> {result.metadata.warnings.length} {result.metadata.warnings.length === 1 ? "warning" : "warnings"}</summary><ul>{result.metadata.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></details>}
      <div className="viewer-tabs" role="tablist" aria-label="Result view">
        <button role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>Preview</button>
        <button role="tab" aria-selected={tab === "markdown"} onClick={() => setTab("markdown")}>Markdown</button>
        {tab === "markdown" && <button className="copy-button" onClick={copy}>{copied ? <Check size={15} /> : <Clipboard size={15} />}{copied ? "Copied" : "Copy"}</button>}
      </div>
      {tab === "preview" ? (
        <article className="markdown-preview">
          <MarkdownContent markdown={result.markdown} assetBase={assetBase} />
        </article>
      ) : <pre className="raw-markdown"><code>{result.markdown}</code></pre>}
      <div className="download-footer"><span><Download size={15} /> Downloads remain available until the local engine clears this result.</span><button className="text-button" onClick={onReset}><RotateCcw size={14} /> Convert another file</button></div>
    </section>
  );
}

const MarkdownContent = memo(function MarkdownContent({ markdown, assetBase }: { markdown: string; assetBase: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} urlTransform={(url) => url.startsWith("assets/") ? `${assetBase}${url}` : defaultUrlTransform(url)}>{markdown}</ReactMarkdown>;
});

function engineLabel(engine: string): string { return engine === "pymupdf4llm" ? "PyMuPDF4LLM" : engine === "markitdown" ? "MarkItDown" : "Docling"; }
