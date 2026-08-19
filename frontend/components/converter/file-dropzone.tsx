import { FileText, UploadCloud, X } from "lucide-react";
import { useRef, useState } from "react";

interface Props { file: File | null; disabled: boolean; onSelect: (file: File | null) => void; onError: (message: string) => void; }

export function FileDropzone({ file, disabled, onSelect, onError }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const choose = (candidate?: File) => {
    if (!candidate) return;
    if (!/\.(pdf|docx|pptx|xlsx|html?|csv|txt|md)$/i.test(candidate.name)) {
      onError("Select a supported PDF, Office, HTML, CSV, text, or Markdown file."); return;
    }
    onSelect(candidate);
  };
  if (file) return (
    <div className="selected-file">
      <span className="file-icon"><FileText size={22} /></span>
      <span><strong>{file.name}</strong><small>{formatBytes(file.size)} · PDF</small></span>
      <button className="icon-button" onClick={() => onSelect(null)} disabled={disabled} aria-label="Remove selected file"><X size={18} /></button>
    </div>
  );
  return (
    <div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); if (!disabled) choose(e.dataTransfer.files[0]); }}>
      <input ref={inputRef} className="sr-only" id="document-input" type="file" accept=".pdf,.docx,.pptx,.xlsx,.html,.htm,.csv,.txt,.md" onChange={(e) => choose(e.target.files?.[0])} disabled={disabled} />
      <UploadCloud size={28} aria-hidden="true" />
      <p><strong>Drop a document here</strong><span>PDF, Office, HTML, CSV, text, or Markdown</span></p>
      <button className="button secondary" onClick={() => inputRef.current?.click()} disabled={disabled}>Choose file</button>
    </div>
  );
}

function formatBytes(bytes: number): string { return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`; }
