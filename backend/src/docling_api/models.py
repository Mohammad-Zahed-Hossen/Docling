from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EngineName = Literal["auto", "pymupdf4llm", "docling", "markitdown"]
ModeName = Literal["fast", "balanced", "high_accuracy"]
OcrMode = Literal["auto", "off", "force"]
ImageMode = Literal["ignore", "extract"]
DescriptionMode = Literal["off", "smart", "all"]
CpuMode = Literal["balanced", "maximum"]
InputType = Literal["file", "url"]


@dataclass(frozen=True)
class ConversionOptions:
    engine: EngineName = "auto"
    mode: ModeName = "balanced"
    ocr: OcrMode = "auto"
    images: ImageMode = "extract"
    image_descriptions: DescriptionMode = "off"
    cpu: CpuMode = "balanced"
    cache: bool = True


@dataclass(frozen=True)
class DocumentProfile:
    pages: int
    text_characters: int
    digital_text_ratio: float
    scanned_page_ratio: float
    image_density: float
    table_signals: int
    layout_complexity: float
    confidence: float

    @property
    def difficult(self) -> bool:
        return self.scanned_page_ratio >= 0.45 or self.layout_complexity >= 0.72


@dataclass
class EngineResult:
    markdown: str
    pages: int | None = None
    assets: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class UnifiedResult:
    markdown: str
    markdown_path: Path
    package_path: Path
    pages: int | None
    processing_seconds: float
    figures: int
    table_images: int
    engine: str
    engine_reason: str
    warnings: list[str]
    cache_hit: bool
    fallback_reason: str | None = None


@dataclass(frozen=True)
class UrlInput:
    url: str
    input_type: InputType = "url"


@dataclass
class WebExtractionResult:
    title: str | None
    markdown: str
    source_url: str
    author: str | None = None
    published_at: str | None = None
    warnings: list[str] = field(default_factory=list)
