# Unified Markdown Converter

A fast, CPU-first local converter that turns files and public webpages into clean, portable Markdown and structured assets.

---

## Why This Project Exists

Document conversion is rarely one-size-fits-all:

* **Fast digital extractors** parse ordinary digital PDFs in milliseconds, but struggle with scanned pages or complex multi-column layouts.
* **Layout-aware AI parsers** accurately extract scanned PDFs and complex tables, but incur significantly higher CPU latency.
* **General office file converters** handle structured formats (`.docx`, `.pptx`, `.xlsx`), but do not specialize in advanced PDF structural inspection.

Rather than building a custom PDF parser from scratch or forcing every document through a single heavy engine, **Unified Markdown Converter** acts as a local orchestration layer. It evaluates document complexity on the fly, applies fast deterministic paths where possible, and triggers high-fidelity structural fallback only when necessary.

---

## Core Idea & Engine Strategy

The system orchestrates three specialized open-source conversion engines:

| Engine | Role | Best For |
| :--- | :--- | :--- |
| **PyMuPDF4LLM** | Fast PDF Path | Ordinary digital PDFs, papers, books, and reports |
| **Docling** | High-Fidelity Fallback | Scanned PDFs, complex multi-column layouts, and difficult tables |
| **MarkItDown** | General File Converter | DOCX, PPTX, XLSX, HTML, CSV, TXT, and MD files |

### Intelligent Routing Flow

```text
Input File
   │
   ├─ Non-PDF (.docx, .pptx, .xlsx, .html, .csv, .txt, .md) ──► MarkItDown
   │
   └─ PDF Document
        │
        ▼
   Lightweight Inspector (PyMuPDF)
        │
        ├─ Digital / Ordinary Text ──► PyMuPDF4LLM Fast Path
        │                                  │
        │                             Quality Gate
        │                                  │
        │                         Extraction Defect?
        │                           │            │
        │                           │ (No)       │ (Yes)
        │                           ▼            ▼
        │                        Complete     Docling Fallback
        │
        └─ Scanned / Complex Layout ──────────► Docling
```

---

## Key Features

* **Intelligent Auto-Routing**: Dynamically selects the optimal engine based on file format and PDF structural inspection.
* **Quality-Gated Fallback**: Automatically escalates to Docling if the PyMuPDF fast path produces text corruption or low character counts.
* **Deterministic Canonical Normalization**: Standardizes line wraps, headings, lists, code fences, and blank lines across all engines without using an LLM.
* **Asset Extraction & Relative Paths**: Extracts figures and tables into a clean `assets/` directory with stable relative Markdown references (`assets/figure-001.png`).
* **Content Hash Caching**: SHA-256 caching bypasses redundant engine processing for identical files and settings.
* **Strict Loopback Privacy**: Local FastAPI backend binds exclusively to `127.0.0.1:8000`, ensuring document contents never leave your machine.
* **Seamless Windows Autostart**: Background service launcher and menu helper (`scripts/manage-backend.bat`) for background management.
* **Modern Web Interface**: Built with Next.js, supporting real-time Markdown rendering, KaTeX math preview, raw text view, and ZIP downloads.

---

## Supported Inputs

In V1, the converter supports the following input file extensions:

* **PDF** (`.pdf`): Handled via PyMuPDF4LLM (fast path) or Docling (high-fidelity fallback).
* **Office Documents**: Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`).
* **Web & Structured Text**: HTML (`.html`, `.htm`), CSV (`.csv`).
* **Plain Text & Markdown**: Text (`.txt`), Markdown (`.md`).
* **Public Webpages**: Readable HTTP(S) articles and documentation pages, extracted locally with Defuddle.
* **Direct Document URLs**: PDF, DOCX, PPTX, and XLSX links are downloaded with strict limits and routed through the existing file engines.

*Note: In V1, PyMuPDF4LLM and Docling engine routes are dedicated to PDF processing, while non-PDF formats are routed through MarkItDown.*

### URL → Markdown

Select **URL**, paste a public article or documentation URL, and choose whether useful content
images should be ignored or preserved. The backend performs a bounded fetch, extracts the main
readable content locally with Defuddle, passes it through the canonical Markdown layer, and adds
the final source URL near the top of the document. Preserved images use the existing `assets/`
output contract.

Authenticated, CAPTCHA-protected, paywalled, and heavily JavaScript-rendered pages are
intentionally outside V1 scope. No Chromium, browser automation, hosted extraction API, or LLM
rewriting is used.

---

## Output Contract

Every conversion produces a clean, isolated output bundle:

```text
document-name.md
assets/                 # Created only when images/tables are extracted
├── figure-001.png
├── figure-002.png
└── table-001.png
```

* **Markdown File**: Standard `.md` file containing canonical Markdown.
* **Asset Directory**: Contains extracted figures (`figure-XXX.png`) and tables (`table-XXX.png`).
* **Relative Links**: All image tags inside the Markdown reference relative paths (`![caption](assets/figure-001.png)`).
* **Portable ZIP Package**: Downloadable package contains only the `.md` file and `assets/` directory. Internal cache files and manifest logs remain private.

---

## Markdown Quality & Normalization

Engine outputs are processed through a deterministic normalization pipeline (`markdown.py`) before final saving:

1. **Line Ending & Character Sanitization**: Converts `\r\n` to `\n` and removes null bytes and unprintable ASCII control characters.
2. **Heading & List Standardisation**: Ensures single-space heading prefixes (`# Heading`) and normalizes list markers (`*` and `+` convert to `-`).
3. **Conservative Line-Wrap Repair**: Rejoins soft line breaks from PDF extractions while preserving code blocks, blockquotes, tables, math blocks (`$$`), and punctuated line endings.
4. **Code Fence Integrity**: Validates and auto-closes unclosed triple-backtick code fences.
5. **Path Sanitization**: Strips absolute local filesystem paths (`C:\...` or `file:///...`) from image references.
6. **No Content Rewriting**: Document text is never altered, summarized, or rewritten by an LLM.

---

## Conversion Modes

When converting PDF files, three operational modes govern engine selection:

* **Balanced (Default & Recommended)**: Inspects the PDF structure. Ordinary digital PDFs use PyMuPDF4LLM. If the extraction fails the quality gate (low text yield or encoding corruption), it transparently falls back to Docling. Scanned or highly complex PDFs route directly to Docling.
* **Fast**: Forces PyMuPDF4LLM for all PDF documents and MarkItDown for general formats, prioritizing conversion speed over layout verification.
* **High Accuracy**: Favors Docling for complex PDFs and forced OCR tasks, while retaining the PyMuPDF fast path for simple digital documents.

---

## Architecture

The system decouples the web user interface from the local document conversion engine:

```text
┌─────────────────────────────────────────────────────────┐
│ Next.js Web Frontend (Local or Vercel Hosted)           │
└────────────────────────────┬────────────────────────────┘
                             │ Direct browser requests (HTTP)
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Local FastAPI Backend (Loopback: 127.0.0.1:8000)        │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │ Inspector & Router                              │   │
│   └───────────────┬───────────────┬───────────────┬─┘   │
│                   │               │               │     │
│                   ▼               ▼               ▼     │
│             PyMuPDF4LLM        Docling        MarkItDown│
│                   │               │               │     │
│                   └───────────────┼───────────────┘     │
│                                   ▼                     │
│                     Canonical Markdown Normalizer       │
└───────────────────────────────────┬─────────────────────┘
                                    ▼
                         Result (.md + assets/)
```

URL input follows a separate lightweight adapter path:

```text
Public URL → Safe bounded fetch → Defuddle Web Extractor → Canonical Markdown → .md + assets/
Direct document URL ─────────────────→ Existing file router ────────────────┘
```

* **Decoupled Architecture**: The frontend can run locally or via a Vercel deployment.
* **Local Backend Execution**: All document parsing and OCR take place on your local CPU. The browser sends HTTP requests directly to `http://127.0.0.1:8000`.
* **Zero Cloud Dependency**: Documents never pass through Vercel servers or external cloud LLM APIs.

---

## Repository Structure

```text
Docling/
├── backend/                  # FastAPI service and conversion engine integrations
│   ├── src/docling_api/      # Core logic (router, engines, inspector, normalizer)
│   ├── tests/                # Pytest suite for API and engines
│   └── pyproject.toml        # Backend Python package configuration (uv)
├── frontend/                 # Next.js web application
│   ├── app/                  # Application pages and API client logic
│   └── components/converter/ # React UI components (dropzone, settings, preview)
├── scripts/                  # Windows autostart & background management scripts
│   ├── manage-backend.bat    # Interactive control menu (Status/Start/Stop/Restart)
│   ├── install-autostart.ps1 # Configures Windows Startup entry
│   └── prefetch-models.ps1   # Downloads offline CPU models for Docling
└── README.md                 # Project documentation
```

---

## Daily Use

Once initial setup is complete, daily usage requires no command line interaction:

1. **Start Windows**: The background converter service starts automatically in the background.
2. **Open Web App**: Open your pinned local frontend (`http://localhost:3000`) or hosted UI.
3. **Convert**: Drag and drop a document, or switch to **URL** and paste a public webpage link.
4. **Export Result**: Preview rendered Markdown / math, and download the Markdown file or ZIP package.

### Managing the Backend Service

If you need to check or restart the local backend, run:

```cmd
scripts\manage-backend.bat
```

This interactive script provides options to check service **Status**, **Start**, **Stop**, or **Restart** the backend process.

---

## First-Time Setup

### Prerequisites

* [Git](https://git-scm.com/)
* [Node.js LTS](https://nodejs.org/) (v18+)
* [uv](https://docs.astral.sh/uv/) (Python package manager)

### Installation (Windows)

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/Mohammad-Zahed-Hossen/Docling.git
   cd Docling
   ```

2. **Install Python dependencies**:
   ```powershell
   cd backend
   uv sync
   cd ..
   ```

3. **Install frontend and local Defuddle dependencies**:
   ```powershell
   cd frontend
   npm install
   cd ..
   ```

4. **Prefetch offline OCR & layout models**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\prefetch-models.ps1
   ```

5. **Register Windows background autostart & launch backend**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\install-autostart.ps1
   .\scripts\start-backend.bat
   ```

6. **Verify Backend Health**:
   Navigating to `http://127.0.0.1:8000/api/health` in your browser should return:
   ```json
   {"status":"ok","service":"unified-markdown-converter"}
   ```

---

## Development Setup

### Running Backend in Development Mode

To run the FastAPI backend with live reload:

```powershell
cd backend
uv run uvicorn docling_api.main:app --host 127.0.0.1 --port 8000
```

### Running Frontend in Development Mode

To launch the Next.js development server:

```powershell
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## Configuration

The backend works out of the box with sensible defaults. Optional environment variables can be configured in `backend/.env` (see `backend/.env.example`):

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | CORS allowed origins for frontend communication |
| `MAX_UPLOAD_MB` | `100` | Maximum file upload size limit in megabytes |
| `RESULT_TTL_MINUTES` | `60` | Time-to-live before temporary conversion outputs are pruned |
| `DOCLING_CPU_THREADS` | `6` | CPU threads allocated to Docling processing |
| `DOCLING_TABLE_MODE` | `fast` | Docling table extraction strategy (`fast` or `accurate`) |
| `DOCLING_OCR_BITMAP_THRESHOLD` | `0.15` | Minimum bitmap ratio to trigger OCR scan |

---

## Caching Strategy

The converter computes a SHA-256 digest based on the file content and active conversion options (engine selection, mode, OCR settings). 

When a matching digest is found in `.cache/`:
* The existing Markdown file and asset folder are instantly restored.
* Heavy conversion engines are completely bypassed.
* API responses include `"cache_hit": true`.

---

## Image & VLM Behavior

* **Image Extraction**: Extracted figures and tables are organized into `assets/` with relative Markdown tags (`![caption](assets/figure-001.png)`).
* **Image Descriptions**: The UI includes settings for `Off`, `Smart`, and `All`. 
* **VLM Model Status**: This repository **does not bundle or download a Vision Language Model (VLM)**. Selecting `Smart` or `All` preserves existing document captions and returns a warning: `"Local image descriptions are not configured; captions were preserved."` This intentional design keeps the installation lightweight and avoids heavy CPU vision inference.

---

## REST API Overview

The backend exposes a minimal RESTful API over HTTP loopback (`http://127.0.0.1:8000`):

### Endpoints

* `GET /api/health`: Returns service health status.
* `POST /api/convert`: Accepts multipart form uploads and returns Markdown content and download URLs.
* `POST /api/convert-url`: Accepts a public URL plus image/cache preferences.
* `GET /api/results/{result_id}/markdown`: Downloads the output `.md` file.
* `GET /api/results/{result_id}/package`: Downloads the `.zip` archive containing `.md` and `assets/`.
* `GET /api/results/{result_id}/assets/{asset_name}`: Serves individual asset images.

### Conversion Form Options (`POST /api/convert`)

* `file`: Multipart file stream (Required).
* `converter`: `auto` (default), `pymupdf4llm`, `docling`, `markitdown`.
* `mode`: `balanced` (default), `fast`, `high_accuracy`.
* `ocr`: `auto` (default), `off`, `force`.
* `images`: `extract` (default), `ignore`.
* `image_descriptions`: `off` (default), `smart`, `all`.
* `cpu`: `balanced` (default), `maximum`.
* `cache`: `true` (default), `false`.

### Concurrency & Error Format

To protect local system memory and CPU resources, conversion execution is serialized. If a conversion is already in progress, concurrent requests receive a `409 Conflict` response with error code `BACKEND_BUSY`.

All errors use a standardized response format:

```json
{
  "error": {
    "code": "UNSUPPORTED_FORMAT",
    "message": "This file format is not supported."
  }
}
```

URL fetching accepts HTTP(S) only and blocks localhost, private/link-local/non-public IP addresses,
including every redirect target. It also enforces TLS verification, connection/total timeouts,
redirect limits, response/content-type limits, and bounded image downloads.

---

## Performance & Quality Verification

### Benchmarking Tool

Run the unified benchmark script to evaluate routing decisions and conversion speeds across sample documents:

```powershell
cd backend
uv run python scripts/benchmark_unified.py "C:\path\to\document.pdf" "C:\path\to\notes.docx"
```

### Code Quality & Testing

Run backend tests and linters:

```powershell
cd backend
uv run ruff check src tests scripts
uv run pytest
```

Run frontend linting and production build verification:

```powershell
cd frontend
npm run lint
npm run build
```

---

## Technical Limitations

* **Single-File Processing**: The API processes one file per request; batch document queues are not implemented in V1.
* **CPU Speed Dependencies**: Docling conversion on complex scanned PDFs depends heavily on host CPU thread count.
* **No Vision Language Model**: Local VLM image descriptions are not bundled to prevent excessive RAM/CPU usage.
* **Local Backend Dependency**: The web UI requires the FastAPI service running locally on `127.0.0.1:8000`.
* **Lightweight Web Extraction**: Login, paywall, CAPTCHA, and pages whose meaningful content exists only after client-side rendering are not supported.

---

## License

No explicit open-source license file is currently included in this repository. Refer to individual third-party engine licenses for upstream usage terms.

---

## Acknowledgments & Third-Party Engines

This project orchestrates and standardizes outputs from three open-source document conversion libraries:

* **[PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)**: Fast PDF to Markdown conversion powered by PyMuPDF.
* **[Docling](https://github.com/DS4SD/docling)**: Deep layout analysis and document parsing by IBM Research.
* **[MarkItDown](https://github.com/microsoft/markitdown)**: Multi-format document conversion framework by Microsoft.
