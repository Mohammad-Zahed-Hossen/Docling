import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import Settings, get_settings
from .converter import DoclingEngine
from .filesystem import ResultStore, safe_stem
from .schemas import (
    ConversionMetadata,
    ConversionResponse,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
)

logger = logging.getLogger("docling_api")


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def create_app(settings: Settings | None = None, engine: DoclingEngine | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    logging.basicConfig(level=app_settings.log_level)
    store = ResultStore(app_settings.temp_directory, app_settings.result_ttl_minutes)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.engine = engine or DoclingEngine()
        application.state.store = store
        await run_in_threadpool(store.prune_expired)
        yield

    application = FastAPI(
        title="Docling Local Engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = app_settings
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
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorBody(code="INVALID_FILE", message="A PDF file is required.")
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @application.post("/api/convert", response_model=ConversionResponse)
    async def convert(file: Annotated[UploadFile, File(...)]) -> ConversionResponse:
        await run_in_threadpool(store.prune_expired)
        filename = file.filename or ""
        if Path(filename).suffix.lower() != ".pdf":
            raise ApiError(415, "INVALID_FILE", "Only PDF files are supported.")
        if file.content_type not in {"application/pdf", "application/octet-stream", None}:
            raise ApiError(415, "INVALID_FILE", "Only PDF files are supported.")

        result_id, job_dir, result_dir = store.create_job()
        input_path = job_dir / "input.pdf"
        try:
            size = await _save_limited_upload(file, input_path, app_settings.max_upload_bytes)
            if size == 0:
                raise ApiError(400, "INVALID_FILE", "The uploaded PDF is empty.")
            if not await run_in_threadpool(_has_pdf_signature, input_path):
                raise ApiError(415, "INVALID_FILE", "The uploaded file is not a valid PDF.")

            active_engine: DoclingEngine = application.state.engine
            if not active_engine.lock.acquire(blocking=False):
                raise ApiError(
                    409, "ENGINE_BUSY", "The local engine is already converting a document."
                )
            try:
                output_stem = safe_stem(filename)
                artifacts = await run_in_threadpool(
                    active_engine.convert, input_path, result_dir, output_stem
                )
            finally:
                active_engine.lock.release()
        except ApiError:
            store.cleanup_result(result_dir)
            raise
        except Exception:
            store.cleanup_result(result_dir)
            logger.exception("Document conversion failed")
            raise ApiError(
                500, "CONVERSION_FAILED", "Docling could not convert this PDF."
            ) from None
        finally:
            await file.close()
            store.cleanup_job(job_dir)

        return ConversionResponse(
            result_id=result_id,
            markdown=artifacts.markdown,
            markdown_url=f"/api/results/{result_id}/markdown",
            package_url=f"/api/results/{result_id}/package",
            metadata=ConversionMetadata(
                original_filename=filename,
                output_filename=artifacts.markdown_path.name,
                pages=artifacts.pages,
                processing_seconds=artifacts.processing_seconds,
                figures=artifacts.figures,
                table_images=artifacts.table_images,
            ),
        )

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
        if not path.is_file() or path.suffix.lower() != ".png":
            raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
        return FileResponse(path, media_type="image/png")

    return application


async def _save_limited_upload(upload: UploadFile, destination: Path, limit: int) -> int:
    total = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ApiError(413, "FILE_TOO_LARGE", "The PDF exceeds the configured size limit.")
            output.write(chunk)
    return total


def _has_pdf_signature(path: Path) -> bool:
    with path.open("rb") as source:
        return source.read(5) == b"%PDF-"


def _find_result(store: ResultStore, result_id: str, pattern: str) -> Path:
    if not result_id.isalnum() or len(result_id) != 32:
        raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
    result_dir = store.results_root / result_id
    matches = list(result_dir.glob(pattern)) if result_dir.is_dir() else []
    if len(matches) != 1:
        raise ApiError(404, "RESULT_NOT_FOUND", "This result is unavailable or has expired.")
    return matches[0]


app = create_app()
