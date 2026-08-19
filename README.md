# Docling

Docling is a single-purpose document utility for converting complex academic PDFs into layout-aware Markdown with [IBM Docling](https://github.com/docling-project/docling). It provides a safe in-browser preview, raw Markdown copy, a Markdown download, and a ZIP containing Markdown plus extracted figure and table images.

## Architecture

```text
Vercel (static Next.js frontend)
              │ browser fetch from the client
              ▼
http://127.0.0.1:8000 (local FastAPI service)
              │
              ▼
        Docling on Windows
              │
              ├── Markdown
              ├── assets/*.png
              └── ZIP package
```

The PDF request originates in the browser and goes directly to the loopback FastAPI service. There is no Next.js API route, Vercel proxy, telemetry, analytics, cloud storage, or external document upload in this project.

The backend is local because Docling has substantial native/model runtime requirements and local execution keeps this personal workflow under the user's control. The backend binds to `127.0.0.1` by default, so it is not exposed to the LAN.

## Prerequisites

- Git
- Node.js (current LTS or newer)
- [uv](https://docs.astral.sh/uv/)
- Python 3.12, managed by uv (uv can install it automatically)

Do not install project Python packages globally.

## Backend setup

```powershell
cd backend
uv sync
uv run python -m docling_api
```

Open `http://127.0.0.1:8000/api/health` to verify the service. The normal response is:

```json
{"status":"ok","service":"docling-local-engine"}
```

The first real conversion downloads Docling/OCR model files and may take substantially longer than later conversions. No API token is required.

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The default local engine URL is `http://127.0.0.1:8000`; it can be changed and reset from Settings. The value is stored only in browser `localStorage`.

## Development and checks

Run the backend and frontend in separate terminals. Useful checks are:

```powershell
cd backend
uv sync
uv run pytest
uv run ruff check .

cd ..\frontend
npm run lint
npm run build
```

Unit tests mock the expensive conversion boundary. For an integration check, start the backend and submit a small real PDF through the UI.

## Windows normal usage

Double-click:

```text
scripts\start-backend.bat
```

It locates `backend`, checks for uv, and starts the production server at `127.0.0.1:8000` without reload mode. Keep its terminal window open; press `Ctrl+C` or close the window to stop it.

For a desktop shortcut, right-click `scripts\start-backend.bat`, choose **Show more options → Send to → Desktop (create shortcut)**, and rename the shortcut to `Docling Local Engine`. A visible window is intentional so the process can be stopped or restarted without leaving an invisible orphan.

## API and result lifecycle

`POST /api/convert` accepts one multipart field named `file`. It validates extension, content type, size, PDF signature, and emptiness, then processes one conversion at a time. A concurrent request receives `ENGINE_BUSY` instead of starting another model pipeline.

The response contains Markdown, honest conversion metadata, a result identifier, and relative URLs for the Markdown and ZIP downloads. Images are never base64-encoded into frontend state. Input jobs are deleted after each request; results live in the operating-system temporary directory and expire after 60 minutes by default. Expired results are pruned on startup and when another conversion begins.

Errors follow one JSON shape:

```json
{"error":{"code":"INVALID_FILE","message":"Only PDF files are supported."}}
```

Internal tracebacks and filesystem paths are logged locally, not returned to the browser.

## Output format

The ZIP has no unnecessary outer directory:

```text
paper-docling.zip
├── paper.md
└── assets/
    ├── figure-001.png
    └── table-001.png
```

Markdown uses relative forward-slash references such as `assets/figure-001.png`, making the extracted folder convenient for Markdown tools, including Notion's **Import → Text & Markdown** workflow. A table remains structured Markdown when Docling recovers it; a rendered table image is additionally included when available.

## Configuration

Backend defaults work without an `.env`. Copy `backend/.env.example` to `backend/.env` only when configuration is needed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Launcher/server bind host |
| `PORT` | `8000` | Launcher/server port |
| `MAX_UPLOAD_MB` | `100` | Upload limit |
| `ALLOWED_ORIGINS` | local development origins | Comma-separated exact frontend origins |
| `TEMP_DIRECTORY` | OS temp directory | Job/result root |
| `RESULT_TTL_MINUTES` | `60` | Temporary result lifetime |
| `LOG_LEVEL` | `INFO` | Local logging level |

The included launcher uses these centralized settings and defaults to the security-sensitive loopback address `127.0.0.1:8000`. If an exact production Vercel origin is used, add it to `ALLOWED_ORIGINS`, for example:

```dotenv
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://your-app.vercel.app
```

Do not use `*`.

## Vercel deployment

Connect this GitHub repository to Vercel using:

- Framework Preset: **Next.js**
- Root Directory: **frontend**
- Build Command: default (`next build`)
- Output Directory: default
- Environment variables: none required

Commits to the configured production branch deploy only the frontend. The Python backend is not part of the Vercel build.

After deployment, add the exact HTTPS deployment origin to the local backend's `ALLOWED_ORIGINS`, restart the backend, and use the frontend Settings panel to confirm `http://127.0.0.1:8000`.

## Installed web app

The frontend includes a web app manifest, theme metadata, and an app icon, so supported Chromium browsers can open it in a standalone app window through **Install this site as an app**. A service worker is intentionally omitted: document conversion requires the local backend and the UI is not presented as offline-capable.

## Troubleshooting

- **`uv` is unavailable:** install uv, reopen the terminal, and confirm `uv --version` works. Do not activate `.venv` manually.
- **Backend is disconnected:** run `scripts\start-backend.bat`, visit `/api/health`, then choose **Retry connection** in the UI.
- **First conversion is slow:** Docling may download and initialize local OCR/layout models. Keep the launcher window open and wait for completion.
- **CORS error:** add the frontend's exact origin (scheme, host, and port) to `ALLOWED_ORIGINS`, then restart the backend.
- **Vercel UI works but says disconnected:** deployment covers only the UI. The Windows backend must be running on the same computer as the browser.
- **Browser blocks localhost/private-network access:** allow the browser's local-network permission if prompted, verify no extension or corporate policy blocks loopback HTTP, and test `/api/health` directly. The PDF is not processed by Vercel.
- **Timeout or engine disappears:** restart the launcher and retry. The frontend uses a 30-minute conversion timeout and reports local connectivity separately.
- **Conversion fails:** inspect the visible backend window for local diagnostics. The browser intentionally receives only a safe error message.

## Repository setup

The repository is intended for `https://github.com/Mohammad-Zahed-Hossen/Docling.git`. After reviewing the working tree:

```powershell
git add .
git commit -m "feat: initialize Docling web and local processing app"
git push -u origin main
```

Never force-push over unrelated remote history.
