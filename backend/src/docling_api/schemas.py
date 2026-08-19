from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["docling-local-engine"] = "docling-local-engine"


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


class ConversionResponse(BaseModel):
    result_id: str
    markdown: str
    markdown_url: str
    package_url: str
    metadata: ConversionMetadata
