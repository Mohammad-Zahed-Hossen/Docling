"use client";

import { AlertCircle, CheckCircle2, ChevronRight, LoaderCircle, LockKeyhole, RefreshCw, Settings } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { checkHealth, checkHealthWithRetry, convertDocument, convertUrl, LocalEngineError, normalizeApiUrl } from "@/lib/api";
import { API_URL_STORAGE_KEY, AUTO_RECONNECT_INTERVAL_MS, DEFAULT_API_URL, MAX_CLIENT_FILE_MB, OPTIONS_STORAGE_KEY, STARTUP_HEALTH_ATTEMPTS, STARTUP_HEALTH_DELAY_MS, THEME_STORAGE_KEY } from "@/lib/constants";
import type { AppTheme, ConnectionState, ConversionOptions, ConversionResult, InputType } from "@/lib/types";
import { MarkIcon } from "@/components/ui/icons";
import { FileDropzone } from "./file-dropzone";
import { ResultViewer } from "./result-viewer";
import { SettingsPanel } from "./settings-panel";

const DEFAULT_OPTIONS: ConversionOptions = { converter: "auto", mode: "balanced", ocr: "auto", images: "extract", image_descriptions: "off", cpu: "balanced", cache: true };

export function ConverterWorkspace() {
  const [apiUrl, setApiUrlState] = useState(DEFAULT_API_URL);
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [theme, setThemeState] = useState<AppTheme>("solarized-light");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [inputType, setInputType] = useState<InputType>("file");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [processing, setProcessing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<ConversionOptions>(DEFAULT_OPTIONS);
  const urlRef = useRef<HTMLInputElement>(null);
  const validUrl = isHttpUrl(url);

  const retry = useCallback(async (value = apiUrl, attempts = 1) => {
    setConnection("checking"); setError(null);
    try { setConnection((await checkHealthWithRetry(value, attempts, STARTUP_HEALTH_DELAY_MS)) ? "connected" : "disconnected"); } catch { setConnection("disconnected"); }
  }, [apiUrl]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const initial = window.localStorage.getItem(API_URL_STORAGE_KEY)?.trim() || DEFAULT_API_URL;
      const activeTheme = (window.localStorage.getItem(THEME_STORAGE_KEY) as AppTheme | null) || "solarized-light";
      setThemeState(activeTheme);
      if (activeTheme === "system") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", activeTheme);
      const stored = window.localStorage.getItem(OPTIONS_STORAGE_KEY);
      if (stored) try { setOptions((current) => ({ ...current, ...JSON.parse(stored) as Partial<ConversionOptions> })); } catch { /* stale settings */ }
      setApiUrlState(initial); void retry(initial, STARTUP_HEALTH_ATTEMPTS);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (inputType === "url") window.setTimeout(() => urlRef.current?.focus(), 0); }, [inputType]);
  useEffect(() => { if (!processing) return; const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000); return () => window.clearInterval(timer); }, [processing]);
  useEffect(() => { if (connection !== "disconnected") return; const timer = window.setInterval(async () => { try { if (await checkHealth(normalizeApiUrl(apiUrl))) setConnection("connected"); } catch { /* retry */ } }, AUTO_RECONNECT_INTERVAL_MS); return () => window.clearInterval(timer); }, [connection, apiUrl]);

  const updateTheme = (value: AppTheme) => { setThemeState(value); window.localStorage.setItem(THEME_STORAGE_KEY, value); if (value === "system") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", value); };
  const updateOptions = (value: ConversionOptions) => { setOptions(value); window.localStorage.setItem(OPTIONS_STORAGE_KEY, JSON.stringify(value)); };
  const selectFile = (value: File | null) => { if (value && value.size > MAX_CLIENT_FILE_MB * 1024 * 1024) { setError(`The file exceeds the ${MAX_CLIENT_FILE_MB} MB upload limit.`); return; } setFile(value); setResult(null); setError(null); };
  const convert = async () => {
    if ((inputType === "file" && !file) || (inputType === "url" && !validUrl)) return;
    setElapsed(0); setProcessing(true); setError(null); setResult(null);
    try { setResult(inputType === "file" ? await convertDocument(normalizeApiUrl(apiUrl), file!, options) : await convertUrl(normalizeApiUrl(apiUrl), url, options)); }
    catch (caught) { if (caught instanceof LocalEngineError) { setError(caught.message); if (caught.code === "LOCAL_ENGINE_ERROR") setConnection("disconnected"); } else setError("The conversion could not be completed."); }
    finally { setProcessing(false); }
  };

  return <main><header className="app-header"><div className="brand"><MarkIcon /><span><strong>Markdown Converter</strong><small>Local · CPU-first</small></span></div><div className="header-actions"><ConnectionBadge state={connection} /><button className="settings-button" onClick={() => setSettingsOpen(true)}><Settings size={17} /><span>Settings</span></button></div></header><div className="workspace">
    <SettingsPanel open={settingsOpen} apiUrl={apiUrl} onApiUrlChange={(value) => { setApiUrlState(value); window.localStorage.setItem(API_URL_STORAGE_KEY, value); setConnection("disconnected"); }} onReset={() => { setApiUrlState(DEFAULT_API_URL); void retry(DEFAULT_API_URL); }} onClose={() => setSettingsOpen(false)} onRetry={() => void retry()} options={options} onOptionsChange={updateOptions} theme={theme} onThemeChange={updateTheme} inputType={inputType} />
    {!result && !processing && <section className="intro"><span className="eyebrow"><LockKeyhole size={14} /> Processed locally</span><h1>Content to clean Markdown</h1><p>Convert a local document or a public webpage, then inspect or download the result.</p></section>}
    {connection === "disconnected" && <div className="notice warning"><AlertCircle /><span><strong>Local engine unavailable</strong><small>Auto-retrying connection in background…</small></span><button className="button secondary" onClick={() => void retry()}><RefreshCw size={15} /> Retry now</button></div>}
    {connection === "checking" && <p className="connection-message"><LoaderCircle className="spin" size={15} /> Checking local engine…</p>}
    {!result && <section className="converter-card" aria-labelledby="input-title">{processing ? <div className="processing-card"><LoaderCircle className="spin" size={28} /><span className="eyebrow">Conversion in progress</span><h2 id="input-title">Converting {inputType === "file" ? file?.name : new URL(url).hostname}</h2><div className="progress"><span /></div><small>{elapsed}s elapsed</small></div> : <>
      <div className="input-tabs" role="tablist"><button className={inputType === "file" ? "active" : ""} onClick={() => { setInputType("file"); setError(null); }}>File</button><button className={inputType === "url" ? "active" : ""} onClick={() => { setInputType("url"); setError(null); }}>URL</button></div>
      <div className="section-heading"><div><span className="step">01</span><h2 id="input-title">{inputType === "file" ? (file ? "Document selected" : "Choose a document") : "Paste a webpage URL"}</h2><p>{inputType === "file" ? `One supported file, up to ${MAX_CLIENT_FILE_MB} MB.` : "Public HTTP(S) webpages and direct document links."}</p></div></div>
      {inputType === "file" ? <FileDropzone file={file} disabled={false} onSelect={selectFile} onError={setError} /> : <label className="url-field">Webpage URL<input ref={urlRef} type="url" value={url} placeholder="https://example.com/article" spellCheck={false} onChange={(event) => { setUrl(event.target.value); setError(null); }} onKeyDown={(event) => { if (event.key === "Enter" && validUrl) void convert(); }} />{url.trim() && !validUrl && <small>Enter a valid http:// or https:// URL.</small>}</label>}
      {error && <div className="inline-error"><AlertCircle size={18} />{error}</div>}
      <div className="convert-row"><button className="settings-summary" onClick={() => setSettingsOpen(true)}>{inputType === "url" ? `Images ${options.images === "extract" ? "Extract" : "Ignore"} · Cache ${options.cache ? "On" : "Off"}` : settingsSummary(options)} <ChevronRight size={15} /></button><button className="button primary convert-button" onClick={() => void convert()} disabled={connection !== "connected" || (inputType === "file" ? !file : !validUrl)}>Convert to Markdown</button></div>
    </>}</section>}
    {result && <ResultViewer result={result} apiUrl={normalizeApiUrl(apiUrl)} onReset={() => { setFile(null); setUrl(""); setResult(null); setError(null); }} />}
    <footer><LockKeyhole size={14} /> Files process locally; URL mode fetches only the public source and selected images.</footer>
  </div></main>;
}

function ConnectionBadge({ state }: { state: ConnectionState }) { return <span className={`connection ${state}`}>{state === "connected" ? <CheckCircle2 /> : state === "checking" ? <LoaderCircle className="spin" /> : <AlertCircle />}<span>{state === "connected" ? "Local engine connected" : state === "checking" ? "Checking…" : "Engine unavailable"}</span></span>; }
function isHttpUrl(value: string): boolean { try { return ["http:", "https:"].includes(new URL(value.trim()).protocol); } catch { return false; } }
function settingsSummary(options: ConversionOptions): string { const converter = options.converter === "auto" ? "Auto" : options.converter === "pymupdf4llm" ? "PyMuPDF4LLM" : options.converter === "markitdown" ? "MarkItDown" : "Docling"; const mode = options.mode === "high_accuracy" ? "High Accuracy" : options.mode[0].toUpperCase() + options.mode.slice(1); return `${converter} · ${mode} · OCR ${options.ocr === "auto" ? "Auto" : options.ocr === "force" ? "Force" : "Off"}`; }
