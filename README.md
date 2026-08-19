# Unified Markdown Converter

A local-first, CPU-only converter that produces one portable Markdown file and an optional
`assets/` directory. The browser talks directly to a FastAPI service bound to `127.0.0.1`;
documents are not proxied through the hosted Next.js frontend.

## Routing

```text
input
  ├─ supported non-PDF ───────────────► MarkItDown
  └─ PDF ─► lightweight inspection
              ├─ digital/ordinary ────► PyMuPDF4LLM
              │                           └─ poor extraction in Balanced mode ─► Docling
              └─ scanned/complex ─────► Docling
```

Supported V1 inputs: PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT, and MD.

Modes:

- **Fast** uses PyMuPDF4LLM for PDF and MarkItDown for other supported formats.
- **Balanced** is the default. It inspects PDFs, uses the fast path when appropriate, and
  falls back to Docling only when a conservative quality gate detects a poor extraction.
- **High Accuracy** selects Docling for difficult PDFs while retaining the fast path for
  ordinary digital PDFs.

Manual engine selection remains available. Docling and PyMuPDF4LLM are PDF-only in V1.

## Output

The public result is exactly:

```text
document-name.md
assets/                 # only when useful assets were extracted
├── figure-001.png
└── table-001.png
```

The downloadable ZIP contains only that Markdown file and optional assets. Cache manifests,
inspection data, and temporary files remain internal.

Markdown is normalized deterministically: line endings, heading spacing, list markers,
conservative PDF line-wrap repair, blank lines, control characters, code fences, relative
asset paths, and stable asset names. No LLM rewrites document content.

## Daily Windows use

1. Windows starts the local backend through the current-user Startup entry.
2. Open the installed/pinned web app.
3. Drop a supported file, normally leaving **Auto** and **Balanced** selected.
4. Convert, preview, and download the Markdown or package.

VS Code, a terminal, and manual virtual-environment activation are not required for daily use.
Double-click `scripts/manage-backend.bat` for Status, Start, Stop, or Restart.

The launcher prevents duplicate healthy processes, runs without development reload, binds only
to `127.0.0.1`, and writes diagnostics under `runtime/`.

## First-time setup

Requirements: Git, current Node.js LTS, and [uv](https://docs.astral.sh/uv/).

```powershell
cd backend
uv sync
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\prefetch-models.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\install-autostart.ps1
.\scripts\start-backend.bat
```

Health check:

```json
{"status":"ok","service":"unified-markdown-converter"}
```

## Development

```powershell
cd backend
uv run uvicorn docling_api.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

Focused verification:

```powershell
cd backend
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/benchmark_unified.py "C:\path\digital.pdf" "C:\path\notes.docx"

cd ..\frontend
npm run lint
npm run build
```

## API

- `GET /api/health`
- `POST /api/convert`
- result download routes returned by the conversion response

`POST /api/convert` accepts multipart `file` plus `converter`, `mode`, `ocr`, `images`,
`image_descriptions`, `cpu`, and `cache`. One heavy conversion runs at a time. A concurrent
request receives `BACKEND_BUSY`.

Errors use a stable shape without tracebacks or local filesystem paths:

```json
{"error":{"code":"UNSUPPORTED_FORMAT","message":"This file format is not supported."}}
```

## Configuration

Backend defaults work without an `.env`. Relevant optional variables are documented in
`backend/.env.example`, including upload size, allowed frontend origins, result expiry,
Docling CPU threads, table mode, and OCR bitmap threshold.

The cache key includes file content, conversion settings, and the selected Auto result. Repeated
conversions restore Markdown and assets without running an engine again.

## Current image-description behavior

Conversion never requires a VLM. The UI exposes Off, Smart, and All, but this repository does
not bundle a local vision model. When Smart or All is selected, existing captions are preserved
and the result reports that local image descriptions are not configured. This avoids silently
adding a large CPU model without a measured quality and latency benefit.
