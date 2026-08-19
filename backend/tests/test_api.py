from io import BytesIO
from pathlib import Path
from threading import Lock
from zipfile import ZipFile

from fastapi.testclient import TestClient

from docling_api.config import Settings
from docling_api.main import create_app
from docling_api.models import UnifiedResult


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "unified-markdown-converter"}


def test_rejects_unsupported_format(client: TestClient) -> None:
    response = client.post("/api/convert", files={"file": ("notes.exe", b"hello")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_rejects_empty_pdf(client: TestClient) -> None:
    response = client.post("/api/convert", files={"file": ("paper.pdf", b"", "application/pdf")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_rejects_oversized_pdf(client: TestClient) -> None:
    content = b"%PDF-" + b"x" * (1024 * 1024)
    response = client.post(
        "/api/convert", files={"file": ("paper.pdf", BytesIO(content), "application/pdf")}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_converter_failure_is_standardized(tmp_path: Path) -> None:
    class FailingEngine:
        lock = Lock()

        def convert(self, *_args):
            raise RuntimeError("private C:\\path detail")

    app = create_app(Settings(temp_directory=tmp_path), engine=FailingEngine())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/convert", files={"file": ("paper.pdf", b"%PDF-1.7\n", "application/pdf")}
        )
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "CONVERSION_FAILED", "message": "The document could not be converted."}
    }
    assert "path" not in response.text


def test_success_and_downloads(tmp_path: Path) -> None:
    class SuccessfulEngine:
        lock = Lock()

        def convert(self, _input: Path, result_dir: Path, stem: str, _options) -> UnifiedResult:
            md_path = result_dir / f"{stem}.md"
            md_path.write_text("# Test", encoding="utf-8")
            zip_path = result_dir / f"{stem}-docling.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.write(md_path, md_path.name)
            return UnifiedResult(
                "# Test", md_path, zip_path, 1, 0.1, 0, 0, "pymupdf4llm", "Digital PDF.", [], False
            )

    app = create_app(Settings(temp_directory=tmp_path), engine=SuccessfulEngine())
    with TestClient(app) as client:
        response = client.post(
            "/api/convert", files={"file": ("A Paper.pdf", b"%PDF-1.7\n", "application/pdf")}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["markdown"] == "# Test"
        assert client.get(result["markdown_url"]).content == b"# Test"
        assert client.get(result["package_url"]).status_code == 200


def test_busy_engine_returns_clean_response_and_cleans_job(tmp_path: Path) -> None:
    class BusyEngine:
        lock = Lock()

    engine = BusyEngine()
    engine.lock.acquire()
    app = create_app(Settings(temp_directory=tmp_path), engine=engine)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/convert",
                files={"file": ("paper.pdf", b"%PDF-1.7\n", "application/pdf")},
            )
    finally:
        engine.lock.release()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BACKEND_BUSY"
    assert not list((tmp_path / "jobs").iterdir())
    assert not list((tmp_path / "results").iterdir())


def test_default_engine_is_initialized_once_in_lifespan(tmp_path: Path, monkeypatch) -> None:
    created = 0

    class LifecycleEngine:
        lock = Lock()

        def __init__(self, _settings: Settings) -> None:
            nonlocal created
            created += 1

    monkeypatch.setattr("docling_api.main.UnifiedConverter", LifecycleEngine)
    app = create_app(Settings(temp_directory=tmp_path))
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health").status_code == 200
    assert created == 1
