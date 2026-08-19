import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import Settings, get_settings
from .filesystem import ResultStore, safe_stem
from .models import ConversionOptions
from .orchestrator import UnifiedConverter
from .schemas import (
    ConversionMetadata,
    ConversionResponse,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    UrlConversionRequest,
)
from .web_extractor import WebExtractor
from .web_fetcher import WebError, fetch_url, write_direct_document

logger = logging.getLogger("docling_api")
SUPPORTED = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".csv", ".txt", ".md"}


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code, self.code, self.message = status_code, code, message


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    app_settings = settings or get_settings()
    logging.basicConfig(level=app_settings.log_level)
    store = ResultStore(app_settings.temp_directory, app_settings.result_ttl_minutes)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.engine = engine or UnifiedConverter(app_settings)
        application.state.store = store
        await run_in_threadpool(store.prune_expired)
        yield

    application = FastAPI(
        title="Unified Markdown Converter", version="1.0.0", redoc_url=None, lifespan=lifespan
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        payload = ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message))
        return JSONResponse(content=payload.model_dump(), status_code=exc.status_code)

    @application.exception_handler(WebError)
    async def web_error_handler(_request: Request, exc: WebError) -> JSONResponse:
        payload = ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message))
        return JSONResponse(content=payload.model_dump(), status_code=exc.status_code)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        if request.url.path == "/api/convert-url":
            payload = ErrorResponse(
                error=ErrorBody(code="INVALID_URL", message="Enter a valid public HTTP(S) URL.")
            )
        else:
            payload = ErrorResponse(
                error=ErrorBody(code="INVALID_FILE", message="A supported file is required.")
            )
        return JSONResponse(content=payload.model_dump(), status_code=422)

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @application.post("/api/convert", response_model=ConversionResponse)
    async def convert(
        file: Annotated[UploadFile, File(...)],
        converter: Annotated[str, Form()] = "auto",
        mode: Annotated[str, Form()] = "balanced",
        ocr: Annotated[str, Form()] = "auto",
        images: Annotated[str, Form()] = "extract",
        image_descriptions: Annotated[str, Form()] = "off",
        cpu: Annotated[str, Form()] = "balanced",
        cache: Annotated[bool, Form()] = True,
    ) -> ConversionResponse:
        await run_in_threadpool(store.prune_expired)
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED:
            raise ApiError(415, "UNSUPPORTED_FORMAT", "This file format is not supported.")
        valid = (
            converter in {"auto", "pymupdf4llm", "docling", "markitdown"}
            and mode in {"fast", "balanced", "high_accuracy"}
            and ocr in {"auto", "off", "force"}
            and images in {"ignore", "extract"}
            and image_descriptions in {"off", "smart", "all"}
            and cpu in {"balanced", "maximum"}
        )
        if not valid:
            raise ApiError(422, "INVALID_SETTINGS", "One or more conversion settings are invalid.")
        options = ConversionOptions(
            engine=converter,
            mode=mode,
            ocr=ocr,
            images=images,
            image_descriptions=image_descriptions,
            cpu=cpu,
            cache=cache,
        )  # type: ignore[arg-type]
        result_id, job_dir, result_dir = store.create_job()
        input_path = job_dir / f"input{suffix}"
        try:
            size = await _save_limited_upload(file, input_path, app_settings.max_upload_bytes)
            if size == 0:
                raise ApiError(400, "INVALID_FILE", "The uploaded file is empty.")
            if suffix == ".pdf" and not await run_in_threadpool(_has_pdf_signature, input_path):
                raise ApiError(415, "INVALID_FILE", "The uploaded file is not a valid PDF.")
            active = application.state.engine
            if not active.lock.acquire(blocking=False):
                raise ApiError(
                    409, "BACKEND_BUSY", "The converter is already processing a document."
                )
            try:
                artifacts = await run_in_threadpool(
                    active.convert, input_path, result_dir, safe_stem(filename), options
                )
            finally:
                active.lock.release()
        except ApiError:
            store.cleanup_result(result_dir)
            raise
        except ValueError as exc:
            store.cleanup_result(result_dir)
            raise ApiError(422, "INVALID_SETTINGS", str(exc)) from None
        except Exception:
            store.cleanup_result(result_dir)
            logger.exception("Document conversion failed")
            raise ApiError(
                500, "CONVERSION_FAILED", "The document could not be converted."
            ) from None
        finally:
            await file.close()
            store.cleanup_job(job_dir)

        metadata = ConversionMetadata(
            original_filename=filename,
            output_filename=artifacts.markdown_path.name,
            pages=artifacts.pages,
            processing_seconds=artifacts.processing_seconds,
            figures=artifacts.figures,
            table_images=artifacts.table_images,
            engine=artifacts.engine,
            engine_reason=artifacts.engine_reason,
            warnings=artifacts.warnings,
            cache_hit=artifacts.cache_hit,
            fallback_reason=artifacts.fallback_reason,
        )
        return ConversionResponse(
            result_id=result_id,
            markdown=artifacts.markdown,
            markdown_url=f"/api/results/{result_id}/markdown",
            package_url=f"/api/results/{result_id}/package",
            metadata=metadata,
        )

    @application.post("/api/convert-url", response_model=ConversionResponse)
    async def convert_url(request: UrlConversionRequest) -> ConversionResponse:
        await run_in_threadpool(store.prune_expired)
        result_id, job_dir, result_dir = store.create_job()
        started = time.perf_counter()
        active = application.state.engine
        try:
            fetched = await run_in_threadpool(fetch_url, request.url, app_settings)
            if not active.lock.acquire(blocking=False):
                raise ApiError(409, "BACKEND_BUSY", "The converter is already processing a document.")
            try:
                if fetched.document_suffix:
                    input_path = await run_in_threadpool(write_direct_document, fetched, job_dir)
                    stem = safe_stem(Path(urlsplit(fetched.final_url).path).name or "document")
                    options = ConversionOptions(images=request.images, cache=request.cache)
                    artifacts = await run_in_threadpool(active.convert, input_path, result_dir, stem, options)
                    artifacts.engine_reason = f"Direct {fetched.document_suffix[1:].upper()} URL detected. {artifacts.engine_reason}"
                else:
                    extractor = WebExtractor(app_settings)
                    provisional_stem = safe_stem(Path(urlsplit(fetched.final_url).path).name or "webpage")
                    key = active.web_cache_key(fetched.final_url, request.images, extractor.version)
                    artifacts = active.restore_web_cache(key, result_dir, provisional_stem, started) if request.cache else None
                    if artifacts is None:
                        extraction = await run_in_threadpool(extractor.extract, fetched.content, fetched.final_url, result_dir, request.images)
                        stem = safe_stem(extraction.title or provisional_stem)
                        artifacts = await run_in_threadpool(active.finalize_web, extraction, result_dir, stem, started, key if request.cache else None)
            finally:
                active.lock.release()
        except (ApiError, WebError):
            store.cleanup_result(result_dir)
            raise
        except Exception:
            store.cleanup_result(result_dir)
            logger.exception("URL conversion failed")
            raise ApiError(500, "WEB_EXTRACTION_FAILED", "Readable content could not be extracted from this page.") from None
        finally:
            store.cleanup_job(job_dir)
        metadata = ConversionMetadata(
            original_filename=fetched.final_url,
            output_filename=artifacts.markdown_path.name,
            pages=artifacts.pages,
            processing_seconds=artifacts.processing_seconds,
            figures=artifacts.figures,
            table_images=artifacts.table_images,
            engine=artifacts.engine,
            engine_reason=artifacts.engine_reason,
            warnings=artifacts.warnings,
            cache_hit=artifacts.cache_hit,
            fallback_reason=artifacts.fallback_reason,
            input_type="url",
            source_url=fetched.final_url,
            source_domain=urlsplit(fetched.final_url).hostname,
        )
        return ConversionResponse(result_id=result_id, markdown=artifacts.markdown, markdown_url=f"/api/results/{result_id}/markdown", package_url=f"/api/results/{result_id}/package", metadata=metadata)

    @application.get("/api/results/{result_id}/markdown")
    async def download_markdown(result_id: str) -> FileResponse:
        path = _find_result(store, result_id, "*.md")
        return FileResponse(path, media_type="text/markdown", filename=path.name)

    @application.get("/api/results/{result_id}/package")
    async def download_package(result_id: str) -> FileResponse:
        path = _find_result(store, result_id, "*.zip")
        return FileResponse(path, media_type="application/zip", filename=path.name)

    @application.get("/api/results/{result_id}/assets/{asset_name}")
    async def result_asset(result_id: str, asset_name: str) -> FileResponse:
        if not result_id.isalnum() or len(result_id) != 32 or Path(asset_name).name != asset_name:
            raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
        path = store.results_root / result_id / "assets" / asset_name
        if not path.is_file():
            raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
        return FileResponse(path)

    return application


async def _save_limited_upload(upload: UploadFile, destination: Path, limit: int) -> int:
    total = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ApiError(413, "FILE_TOO_LARGE", "The file exceeds the configured size limit.")
            output.write(chunk)
    return total


def _has_pdf_signature(path: Path) -> bool:
    with path.open("rb") as source:
        return source.read(5) == b"%PDF-"


def _find_result(store: ResultStore, result_id: str, pattern: str) -> Path:
    if not result_id.isalnum() or len(result_id) != 32:
        raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
    directory = store.results_root / result_id
    matches = list(directory.glob(pattern)) if directory.is_dir() else []
    if len(matches) != 1:
        raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
    return matches[0]


app = create_app()
