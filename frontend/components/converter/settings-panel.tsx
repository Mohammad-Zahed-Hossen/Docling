import { RotateCcw, Settings, X } from "lucide-react";
import { useEffect, useRef } from "react";

interface Props {
  open: boolean;
  apiUrl: string;
  onApiUrlChange: (url: string) => void;
  onReset: () => void;
  onClose: () => void;
  onRetry: () => void;
}

export function SettingsPanel({ open, apiUrl, onApiUrlChange, onReset, onClose, onRetry }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);
  if (!open) return null;
  return (
    <section className="settings-panel" aria-label="Local engine settings">
      <div className="section-heading">
        <div><span className="eyebrow"><Settings size={14} /> Settings</span><h2>Local engine endpoint</h2></div>
        <button className="icon-button" onClick={onClose} aria-label="Close settings"><X size={18} /></button>
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
