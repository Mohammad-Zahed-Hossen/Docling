from pathlib import Path
from threading import Lock
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from docling_api.config import Settings
from docling_api.main import create_app
from docling_api.models import UnifiedResult
from docling_api.web_extractor import WebExtractor
from docling_api.web_fetcher import FetchResult, WebError, validate_public_url


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.com/a", "javascript:alert(1)"]
)
def test_rejects_invalid_url_schemes(url: str) -> None:
    with pytest.raises(WebError) as error:
        validate_public_url(url)
    assert error.value.code == "INVALID_URL"


@pytest.mark.parametrize("url", ["http://localhost/a", "http://127.0.0.1/a", "http://169.254.169.254/latest"])
def test_blocks_private_and_metadata_urls(url: str) -> None:
    with pytest.raises(WebError) as error:
        validate_public_url(url)
    assert error.value.code == "ACCESS_DENIED"


def test_defuddle_extracts_main_article(tmp_path: Path) -> None:
    html = b"""<!doctype html><title>Useful Article</title><nav>Menu Login Pricing</nav>
    <main><article><h1>Useful Article</h1><p>This is the meaningful article body with enough
    readable content to pass the lightweight extraction quality check.</p><h2>Details</h2>
    <p>Additional technical documentation belongs here, with structure and useful links.</p>
    </article></main><footer>Copyright and social links</footer>"""
    result = WebExtractor(Settings(temp_directory=tmp_path)).extract(
        html, "https://example.com/article", tmp_path, "ignore"
    )
    assert result.title == "Useful Article"
    assert "meaningful article body" in result.markdown
    assert "Pricing" not in result.markdown
    assert "Copyright" not in result.markdown


def test_direct_pdf_url_uses_existing_pipeline(tmp_path: Path, monkeypatch) -> None:
    class DirectEngine:
        lock = Lock()

        def convert(self, _input: Path, result_dir: Path, stem: str, _options) -> UnifiedResult:
            markdown = result_dir / f"{stem}.md"
            markdown.write_text("# Direct PDF", encoding="utf-8")
            package = result_dir / f"{stem}.zip"
            with ZipFile(package, "w") as archive:
                archive.write(markdown, markdown.name)
            return UnifiedResult(
                "# Direct PDF",
                markdown,
                package,
                1,
                0.1,
                0,
                0,
                "pymupdf4llm",
                "Digital PDF.",
                [],
                False,
            )

    monkeypatch.setattr(
        "docling_api.main.fetch_url",
        lambda *_args: FetchResult(
            "https://example.com/paper.pdf", "application/pdf", b"%PDF-1.7", ".pdf"
        ),
    )
    with TestClient(create_app(Settings(temp_directory=tmp_path), engine=DirectEngine())) as client:
        response = client.post("/api/convert-url", json={"url": "https://example.com/paper.pdf"})
    assert response.status_code == 200
    result = response.json()
    assert result["metadata"]["engine"] == "pymupdf4llm"
    assert "Direct PDF URL detected" in result["metadata"]["engine_reason"]
    assert result["metadata"]["source_url"] == "https://example.com/paper.pdf"
