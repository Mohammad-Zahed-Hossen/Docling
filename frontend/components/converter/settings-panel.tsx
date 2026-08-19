import { RotateCcw, Settings, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { ConversionOptions } from "@/lib/types";

interface Props {
  open: boolean;
  apiUrl: string;
  onApiUrlChange: (url: string) => void;
  onReset: () => void;
  onClose: () => void;
  onRetry: () => void;
  options: ConversionOptions;
  onOptionsChange: (options: ConversionOptions) => void;
}

export function SettingsPanel({ open, apiUrl, onApiUrlChange, onReset, onClose, onRetry, options, onOptionsChange }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = [...panelRef.current.querySelectorAll<HTMLElement>('button,input,select,[tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("keydown", onKeyDown); previous?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="sheet-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside ref={panelRef} className="settings-panel" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div className="section-heading">
        <div><span className="eyebrow"><Settings size={14} /> Preferences</span><h2 id="settings-title">Conversion settings</h2></div>
        <button ref={closeRef} className="icon-button" onClick={onClose} aria-label="Close settings"><X size={18} /></button>
      </div>
      <fieldset><legend>Conversion</legend>
      <div className="quick-settings">
        <label>Converter<select value={options.converter} onChange={(e) => onOptionsChange({...options, converter: e.target.value as ConversionOptions["converter"]})}><option value="auto">Auto</option><option value="pymupdf4llm">PyMuPDF4LLM</option><option value="docling">Docling</option><option value="markitdown">MarkItDown</option></select></label>
        <label>Mode<select value={options.mode} onChange={(e) => onOptionsChange({...options, mode: e.target.value as ConversionOptions["mode"]})}><option value="fast">Fast</option><option value="balanced">Balanced</option><option value="high_accuracy">High Accuracy</option></select></label>
        <label>OCR<select value={options.ocr} onChange={(e) => onOptionsChange({...options, ocr: e.target.value as ConversionOptions["ocr"]})}><option value="auto">Auto</option><option value="off">Off</option><option value="force">Force</option></select></label>
      </div></fieldset>
      <fieldset><legend>Output</legend>
      <div className="quick-settings">
        <label>Images<select value={options.images} onChange={(e) => onOptionsChange({...options, images: e.target.value as ConversionOptions["images"]})}><option value="extract">Extract</option><option value="ignore">Ignore</option></select></label>
        <label>Image descriptions<select value={options.image_descriptions} onChange={(e) => onOptionsChange({...options, image_descriptions: e.target.value as ConversionOptions["image_descriptions"]})}><option value="off">Off</option><option value="smart">Smart</option><option value="all">All</option></select></label>
      </div></fieldset>
      <fieldset><legend>Performance</legend>
      <div className="quick-settings">
        <label>CPU usage<select value={options.cpu} onChange={(e) => onOptionsChange({...options, cpu: e.target.value as ConversionOptions["cpu"]})}><option value="balanced">Balanced</option><option value="maximum">Maximum</option></select></label>
        <label>Conversion cache<select value={String(options.cache)} onChange={(e) => onOptionsChange({...options, cache: e.target.value === "true"})}><option value="true">On</option><option value="false">Off</option></select></label>
      </div></fieldset>
      <details className="advanced-settings"><summary>Advanced</summary><label className="field-label" htmlFor="api-url">Local engine URL</label>
      <div className="settings-row">
        <input id="api-url" type="url" value={apiUrl} onChange={(e) => onApiUrlChange(e.target.value)} spellCheck={false} />
        <button className="button secondary" onClick={onRetry}>Test connection</button>
      </div>
      <button className="text-button" onClick={onReset}><RotateCcw size={14} /> Reset endpoint</button></details>
    </aside></div>
  );
}
