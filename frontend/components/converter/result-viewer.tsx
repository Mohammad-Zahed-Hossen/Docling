import { Check, Clipboard, Download, FileText, Package } from "lucide-react";
import { useState } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { resultUrl } from "@/lib/api";
import type { ConversionResult } from "@/lib/types";

export function ResultViewer({ result, apiUrl }: { result: ConversionResult; apiUrl: string }) {
  const [tab, setTab] = useState<"preview" | "markdown">("preview");
  const [copied, setCopied] = useState(false);
  const copy = async () => { await navigator.clipboard.writeText(result.markdown); setCopied(true); window.setTimeout(() => setCopied(false), 1800); };
  const assetBase = `${apiUrl.replace(/\/+$/, "")}/api/results/${result.result_id}/`;
  return (
    <section className="result-card" aria-labelledby="result-title">
      <div className="result-topbar">
        <div><span className="eyebrow success"><Check size={14} /> Conversion complete</span><h2 id="result-title">{result.metadata.output_filename}</h2></div>
        <div className="download-group">
          <a className="button secondary" href={resultUrl(apiUrl, result.markdown_url)}><FileText size={16} /> Markdown</a>
          <a className="button primary" href={resultUrl(apiUrl, result.package_url)}><Package size={16} /> Package (.zip)</a>
        </div>
      </div>
      <dl className="metadata">
        {result.metadata.pages !== null && <div><dt>Pages</dt><dd>{result.metadata.pages}</dd></div>}
        <div><dt>Processing time</dt><dd>{result.metadata.processing_seconds.toFixed(1)}s</dd></div>
        <div><dt>Figures</dt><dd>{result.metadata.figures}</dd></div>
        <div><dt>Table images</dt><dd>{result.metadata.table_images}</dd></div>
      </dl>
      <div className="viewer-tabs" role="tablist" aria-label="Result view">
        <button role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>Preview</button>
        <button role="tab" aria-selected={tab === "markdown"} onClick={() => setTab("markdown")}>Markdown</button>
        {tab === "markdown" && <button className="copy-button" onClick={copy}>{copied ? <Check size={15} /> : <Clipboard size={15} />}{copied ? "Copied" : "Copy Markdown"}</button>}
      </div>
      {tab === "preview" ? (
        <article className="markdown-preview">
          <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} urlTransform={(url) => url.startsWith("assets/") ? `${assetBase}${url}` : defaultUrlTransform(url)}>{result.markdown}</ReactMarkdown>
        </article>
      ) : <pre className="raw-markdown"><code>{result.markdown}</code></pre>}
      <div className="download-footer"><Download size={15} /> Downloads remain available until the local engine clears this temporary result.</div>
    </section>
  );
}
