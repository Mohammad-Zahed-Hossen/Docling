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
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);
  if (!open) return null;
  return (
    <section className="settings-panel" aria-label="Local engine settings">
      <div className="section-heading">
        <div><span className="eyebrow"><Settings size={14} /> Settings</span><h2>Local engine endpoint</h2></div>
        <button className="icon-button" onClick={onClose} aria-label="Close settings"><X size={18} /></button>
      </div>
      <div className="quick-settings">
        <label>OCR<select value={options.ocr} onChange={(e) => onOptionsChange({...options, ocr: e.target.value as ConversionOptions["ocr"]})}><option value="auto">Auto</option><option value="off">Off</option><option value="force">Force</option></select></label>
        <label>Images<select value={options.images} onChange={(e) => onOptionsChange({...options, images: e.target.value as ConversionOptions["images"]})}><option value="extract">Extract</option><option value="ignore">Ignore</option></select></label>
        <label>Image descriptions<select value={options.image_descriptions} onChange={(e) => onOptionsChange({...options, image_descriptions: e.target.value as ConversionOptions["image_descriptions"]})}><option value="off">Off</option><option value="smart">Smart</option><option value="all">All</option></select></label>
        <label>CPU usage<select value={options.cpu} onChange={(e) => onOptionsChange({...options, cpu: e.target.value as ConversionOptions["cpu"]})}><option value="balanced">Balanced</option><option value="maximum">Maximum</option></select></label>
        <label>Conversion cache<select value={String(options.cache)} onChange={(e) => onOptionsChange({...options, cache: e.target.value === "true"})}><option value="true">On</option><option value="false">Off</option></select></label>
      </div>
      <label className="field-label" htmlFor="api-url">Backend URL</label>
      <div className="settings-row">
        <input ref={inputRef} id="api-url" type="url" value={apiUrl} onChange={(e) => onApiUrlChange(e.target.value)} spellCheck={false} />
        <button className="button secondary" onClick={onRetry}>Test connection</button>
      </div>
      <button className="text-button" onClick={onReset}><RotateCcw size={14} /> Reset to default</button>
    </section>
  );
}
