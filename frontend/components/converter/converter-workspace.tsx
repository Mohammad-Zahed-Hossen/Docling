"use client";

import { AlertCircle, CheckCircle2, ChevronRight, LoaderCircle, LockKeyhole, RefreshCw, Settings } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { checkHealth, checkHealthWithRetry, convertDocument, LocalEngineError, normalizeApiUrl } from "@/lib/api";
import { API_URL_STORAGE_KEY, AUTO_RECONNECT_INTERVAL_MS, DEFAULT_API_URL, MAX_CLIENT_FILE_MB, OPTIONS_STORAGE_KEY, STARTUP_HEALTH_ATTEMPTS, STARTUP_HEALTH_DELAY_MS, THEME_STORAGE_KEY } from "@/lib/constants";
import type { AppTheme, ConnectionState, ConversionOptions, ConversionResult } from "@/lib/types";
import { MarkIcon } from "@/components/ui/icons";
import { FileDropzone } from "./file-dropzone";
import { ResultViewer } from "./result-viewer";
import { SettingsPanel } from "./settings-panel";

export function ConverterWorkspace() {
  const [apiUrl, setApiUrlState] = useState(DEFAULT_API_URL);
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [theme, setThemeState] = useState<AppTheme>("solarized-light");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<ConversionOptions>({ converter: "auto", mode: "balanced", ocr: "auto", images: "extract", image_descriptions: "off", cpu: "balanced", cache: true });

  const retry = useCallback(async (url = apiUrl, attempts = 1) => {
    setConnection("checking"); setError(null);
    try { setConnection((await checkHealthWithRetry(url, attempts, STARTUP_HEALTH_DELAY_MS)) ? "connected" : "disconnected"); }
    catch { setConnection("disconnected"); }
  }, [apiUrl]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const stored = window.localStorage.getItem(API_URL_STORAGE_KEY);
      const storedOptions = window.localStorage.getItem(OPTIONS_STORAGE_KEY);
      const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY) as AppTheme | null;
      const initial = stored?.trim() || DEFAULT_API_URL;
      const activeTheme: AppTheme = storedTheme || "solarized-light";
      
      setThemeState(activeTheme);
      if (activeTheme === "system") {
        document.documentElement.removeAttribute("data-theme");
      } else {
        document.documentElement.setAttribute("data-theme", activeTheme);
      }

      if (storedOptions) {
        try { setOptions((current) => ({ ...current, ...JSON.parse(storedOptions) as Partial<ConversionOptions> })); } catch { /* Ignore stale preferences. */ }
      }
      setApiUrlState(initial);
      void retry(initial, STARTUP_HEALTH_ATTEMPTS);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (connection !== "disconnected") return;
    const interval = window.setInterval(async () => {
      try {
        const healthy = await checkHealth(normalizeApiUrl(apiUrl));
        if (healthy) setConnection("connected");
      } catch {
        /* Local engine is still booting up */
      }
    }, AUTO_RECONNECT_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [connection, apiUrl]);

  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [processing]);

  const updateTheme = (newTheme: AppTheme) => {
    setThemeState(newTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    if (newTheme === "system") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", newTheme);
    }
  };

  const updateApiUrl = (value: string) => { setApiUrlState(value); window.localStorage.setItem(API_URL_STORAGE_KEY, value); setConnection("disconnected"); };
  const reset = () => { updateApiUrl(DEFAULT_API_URL); void retry(DEFAULT_API_URL); };
  const updateOptions = (value: ConversionOptions) => { setOptions(value); window.localStorage.setItem(OPTIONS_STORAGE_KEY, JSON.stringify(value)); };
  const selectFile = (value: File | null) => {
    if (value && value.size > MAX_CLIENT_FILE_MB * 1024 * 1024) { setError(`The file exceeds the ${MAX_CLIENT_FILE_MB} MB upload limit.`); return; }
    setFile(value); setResult(null); setError(null);
  };
  const convert = async () => {
    if (!file) return;
    setElapsed(0); setProcessing(true); setError(null); setResult(null);
    try { setResult(await convertDocument(normalizeApiUrl(apiUrl), file, options)); }
    catch (caught) { if (caught instanceof LocalEngineError) { setError(caught.message); if (caught.code === "LOCAL_ENGINE_ERROR") setConnection("disconnected"); } else setError("The conversion could not be completed."); }
    finally { setProcessing(false); }
  };

  return (
    <main>
      <header className="app-header">
        <div className="brand"><MarkIcon /><span><strong>Markdown Converter</strong><small>Local · CPU-first</small></span></div>
        <div className="header-actions"><ConnectionBadge state={connection} /><button className="settings-button" onClick={() => setSettingsOpen(true)} aria-label="Open settings" aria-haspopup="dialog"><Settings size={17} /><span>Settings</span></button></div>
      </header>
      <div className="workspace">
        <SettingsPanel open={settingsOpen} apiUrl={apiUrl} onApiUrlChange={updateApiUrl} onReset={reset} onClose={() => setSettingsOpen(false)} onRetry={() => void retry()} options={options} onOptionsChange={updateOptions} theme={theme} onThemeChange={updateTheme} />
        {!result && !processing && <section className="intro"><span className="eyebrow"><LockKeyhole size={14} /> Processed locally</span><h1>Documents to clean Markdown</h1><p>Drop one document, choose how it should be converted, then inspect or download the result.</p></section>}
        {connection === "disconnected" && <div className="notice warning" role="status" aria-live="polite"><AlertCircle /><span><strong>Local engine unavailable</strong><small>Auto-retrying connection in background… Check that the local converter is running.</small></span><button className="button secondary" onClick={() => void retry()}><RefreshCw size={15} /> Retry now</button></div>}
        {connection === "checking" && <p className="connection-message" role="status" aria-live="polite"><LoaderCircle className="spin" size={15} /> Checking local engine…</p>}
        {!result && <>
        <section className="converter-card" aria-labelledby="upload-title">
          {processing ? <div className="processing-card" role="status" aria-live="polite"><LoaderCircle className="spin" size={28} /><span className="eyebrow">Conversion in progress</span><h2 id="upload-title">Converting {file?.name}</h2><p>{settingsSummary(options)}</p><div className="progress"><span /></div><small>{elapsed}s elapsed · Complex documents may take several minutes.</small></div> : <>
            <div className="section-heading"><div><span className="step">01</span><h2 id="upload-title">{file ? "Document selected" : "Choose a document"}</h2><p>One supported file, up to {MAX_CLIENT_FILE_MB} MB.</p></div></div>
            <FileDropzone file={file} disabled={false} onSelect={selectFile} onError={setError} />
            {error && <div className="inline-error" role="alert"><AlertCircle size={18} />{error}</div>}
            <div className="convert-row"><button className="settings-summary" onClick={() => setSettingsOpen(true)}>{settingsSummary(options)} <ChevronRight size={15} /></button><button className="button primary convert-button" onClick={() => void convert()} disabled={!file || connection !== "connected"}>Convert to Markdown</button></div>
          </>}
        </section>
        </>}
        {error && result && <div className="inline-error" role="alert"><AlertCircle size={18} />{error}</div>}
        {result && <ResultViewer result={result} apiUrl={normalizeApiUrl(apiUrl)} onReset={() => { setFile(null); setResult(null); setError(null); }} />}
        <footer><LockKeyhole size={14} /> Processed locally on this computer.</footer>
      </div>
    </main>
  );
}

function ConnectionBadge({ state }: { state: ConnectionState }) {
  return <span className={`connection ${state}`} role="status" aria-live="polite">{state === "connected" ? <CheckCircle2 /> : state === "checking" ? <LoaderCircle className="spin" /> : <AlertCircle />}<span>{state === "connected" ? "Local engine connected" : state === "checking" ? "Checking…" : "Engine unavailable"}</span></span>;
}

function settingsSummary(options: ConversionOptions): string {
  const converter = options.converter === "auto" ? "Auto" : options.converter === "pymupdf4llm" ? "PyMuPDF4LLM" : options.converter === "markitdown" ? "MarkItDown" : "Docling";
  const mode = options.mode === "high_accuracy" ? "High Accuracy" : options.mode[0].toUpperCase() + options.mode.slice(1);
  const ocr = options.ocr === "auto" ? "OCR Auto" : options.ocr === "force" ? "OCR Force" : "OCR Off";
  return `${converter} · ${mode} · ${ocr}`;
}
