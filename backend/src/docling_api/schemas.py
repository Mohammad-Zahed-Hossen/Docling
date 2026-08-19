from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["unified-markdown-converter"] = "unified-markdown-converter"


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class ConversionMetadata(BaseModel):
    original_filename: str
    output_filename: str
    pages: int | None = None
    processing_seconds: float
    figures: int
    table_images: int
    engine: str
    engine_reason: str
    warnings: list[str] = []
    cache_hit: bool = False
    fallback_reason: str | None = None
    input_type: Literal["file", "url"] = "file"
    source_url: str | None = None
    source_domain: str | None = None


class ConversionResponse(BaseModel):
    result_id: str
    markdown: str
    markdown_url: str
    package_url: str
    metadata: ConversionMetadata


class UrlConversionRequest(BaseModel):
    url: str
    images: Literal["ignore", "extract"] = "extract"
    cache: bool = True
