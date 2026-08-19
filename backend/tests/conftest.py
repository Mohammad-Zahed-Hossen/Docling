from pathlib import Path
from threading import Lock

import pytest
from fastapi.testclient import TestClient

from docling_api.config import Settings
from docling_api.main import create_app


class FakeEngine:
    def __init__(self, error: Exception | None = None) -> None:
        self.lock = Lock()
        self.error = error

    def convert(self, _input_path: Path, _result_dir: Path, _output_stem: str, _options):
        if self.error:
            raise self.error
        raise AssertionError("Unexpected conversion call")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(temp_directory=tmp_path, max_upload_mb=1)
    with TestClient(create_app(settings=settings, engine=FakeEngine())) as test_client:
        yield test_client
