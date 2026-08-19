"use client";

import { AlertCircle, CheckCircle2, LoaderCircle, LockKeyhole, RefreshCw, Settings } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { checkHealth, convertPdf, LocalEngineError, normalizeApiUrl } from "@/lib/api";
import { API_URL_STORAGE_KEY, DEFAULT_API_URL, MAX_CLIENT_FILE_MB } from "@/lib/constants";
import type { ConnectionState, ConversionResult } from "@/lib/types";
import { MarkIcon } from "@/components/ui/icons";
import { FileDropzone } from "./file-dropzone";
import { ResultViewer } from "./result-viewer";
import { SettingsPanel } from "./settings-panel";

export function ConverterWorkspace() {
  const [apiUrl, setApiUrlState] = useState(DEFAULT_API_URL);
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const retry = useCallback(async (url = apiUrl) => {
    setConnection("checking"); setError(null);
    try { setConnection((await checkHealth(url)) ? "connected" : "disconnected"); }
    catch { setConnection("disconnected"); }
  }, [apiUrl]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const stored = window.localStorage.getItem(API_URL_STORAGE_KEY);
      const initial = stored || DEFAULT_API_URL;
      setApiUrlState(initial);
      void retry(initial);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateApiUrl = (value: string) => { setApiUrlState(value); window.localStorage.setItem(API_URL_STORAGE_KEY, value); setConnection("disconnected"); };
  const reset = () => { updateApiUrl(DEFAULT_API_URL); void retry(DEFAULT_API_URL); };
  const selectFile = (value: File | null) => {
    if (value && value.size > MAX_CLIENT_FILE_MB * 1024 * 1024) { setError(`The PDF exceeds the ${MAX_CLIENT_FILE_MB} MB upload limit.`); return; }
    setFile(value); setResult(null); setError(null);
  };
  const convert = async () => {
    if (!file) return;
    setProcessing(true); setError(null); setResult(null);
    try { setResult(await convertPdf(normalizeApiUrl(apiUrl), file)); }
    catch (caught) { if (caught instanceof LocalEngineError) { setError(caught.message); if (caught.code === "LOCAL_ENGINE_ERROR") setConnection("disconnected"); } else setError("The conversion could not be completed."); }
    finally { setProcessing(false); }
  };

  return (
    <main>
      <header className="app-header">
        <div className="brand"><MarkIcon /><span><strong>Docling</strong><small>Local document converter</small></span></div>
        <div className="header-actions"><ConnectionBadge state={connection} /><button className="icon-button" onClick={() => setSettingsOpen((v) => !v)} aria-label="Open local engine settings"><Settings size={18} /></button></div>
      </header>
      <div className="workspace">
        <SettingsPanel open={settingsOpen} apiUrl={apiUrl} onApiUrlChange={updateApiUrl} onReset={reset} onClose={() => setSettingsOpen(false)} onRetry={() => void retry()} />
        <section className="intro"><span className="eyebrow"><LockKeyhole size={14} /> Private, local processing</span><h1>PDF to layout-aware Markdown</h1><p>Your browser sends the selected PDF directly to Docling running on this computer. The Vercel frontend never proxies the document.</p></section>
        {connection === "disconnected" && <div className="notice warning" role="status"><AlertCircle /><span><strong>Local engine is not running</strong><small>Start Docling Local Engine on this computer, then retry the connection.</small></span><button className="button secondary" onClick={() => void retry()}><RefreshCw size={15} /> Retry connection</button></div>}
        <section className="converter-card" aria-labelledby="upload-title">
          <div className="section-heading"><div><span className="step">01</span><h2 id="upload-title">Choose a document</h2><p>One academic PDF, up to {MAX_CLIENT_FILE_MB} MB.</p></div></div>
          <FileDropzone file={file} disabled={processing} onSelect={selectFile} onError={setError} />
          {error && <div className="inline-error" role="alert"><AlertCircle size={18} />{error}</div>}
          <div className="convert-row"><span>{connection === "connected" ? "Ready for local conversion" : "Connect the local engine to continue"}</span><button className="button primary convert-button" onClick={() => void convert()} disabled={!file || connection !== "connected" || processing}>{processing ? <><LoaderCircle className="spin" size={18} /> Converting document…</> : "Convert Document"}</button></div>
          {processing && <div className="progress" role="status"><span /> Docling is analyzing layout, tables, equations, and figures. Large documents can take several minutes.</div>}
        </section>
        {result && <ResultViewer result={result} apiUrl={normalizeApiUrl(apiUrl)} />}
        <footer><LockKeyhole size={14} /> No telemetry, cloud storage, or external document upload.</footer>
      </div>
    </main>
  );
}

function ConnectionBadge({ state }: { state: ConnectionState }) {
  return <span className={`connection ${state}`}>{state === "connected" ? <CheckCircle2 /> : state === "checking" ? <LoaderCircle className="spin" /> : <AlertCircle />}<span>{state === "connected" ? "Connected" : state === "checking" ? "Checking…" : "Disconnected"}</span></span>;
}
