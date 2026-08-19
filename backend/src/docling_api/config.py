from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Annotated, Literal

import psutil
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    max_upload_mb: int = Field(default=100, ge=1, le=1000)
    max_webpage_mb: int = Field(default=10, ge=1, le=50)
    max_web_image_mb: int = Field(default=8, ge=1, le=25)
    max_web_images: int = Field(default=8, ge=0, le=25)
    web_connect_timeout_seconds: float = Field(default=8, ge=1, le=30)
    web_total_timeout_seconds: float = Field(default=20, ge=3, le=120)
    web_redirect_limit: int = Field(default=5, ge=0, le=10)
    web_cache_ttl_hours: int = Field(default=6, ge=1, le=168)
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://docling-azure.vercel.app",
    ]
    temp_directory: Path = Path(gettempdir()) / "docling-local-engine"
    result_ttl_minutes: int = Field(default=60, ge=5, le=1440)
    log_level: str = "INFO"
    docling_cpu_threads: int = Field(default_factory=lambda: _balanced_cpu_threads(), ge=1, le=64)
    docling_table_mode: Literal["fast", "accurate"] = "fast"
    docling_profile_timings: bool = True
    docling_ocr_bitmap_threshold: float = Field(default=0.15, ge=0.01, le=1.0)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_webpage_bytes(self) -> int:
        return self.max_webpage_mb * 1024 * 1024

    @property
    def max_web_image_bytes(self) -> int:
        return self.max_web_image_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _balanced_cpu_threads() -> int:
    physical = psutil.cpu_count(logical=False)
    logical = psutil.cpu_count(logical=True) or 4
    if physical:
        return max(2, min(8, physical))
    return max(2, min(8, logical - 2))
