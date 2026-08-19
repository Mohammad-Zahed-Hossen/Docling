import logging
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrAutoOptions, PdfPipelineOptions, TableFormerMode
from docling.datamodel.settings import settings as docling_settings
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, TableItem

from .config import Settings

logger = logging.getLogger("docling_api.performance")


@dataclass(frozen=True)
class ConversionArtifacts:
    markdown: str
    markdown_path: Path
    zip_path: Path
    pages: int | None
    processing_seconds: float
    figures: int
    table_images: int
    timings: dict[str, float] = field(default_factory=dict)


class DoclingEngine:
    """One reusable converter protected by a single-conversion lock."""

    def __init__(self, settings: Settings) -> None:
        initialized_at = time.perf_counter()
        options = PdfPipelineOptions()
        options.accelerator_options = AcceleratorOptions(
            num_threads=settings.docling_cpu_threads,
            device=AcceleratorDevice.CPU,
        )
        options.do_ocr = True
        options.ocr_options = OcrAutoOptions(
            force_full_page_ocr=False,
            bitmap_area_threshold=settings.docling_ocr_bitmap_threshold,
        )
        options.do_table_structure = True
        options.table_structure_options.mode = TableFormerMode(settings.docling_table_mode)
        options.generate_page_images = False
        options.generate_picture_images = True
        options.generate_table_images = True
        docling_settings.debug.profile_pipeline_timings = settings.docling_profile_timings
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        self._converter.initialize_pipeline(InputFormat.PDF)
        self.initialization_seconds = time.perf_counter() - initialized_at
        self.cpu_threads = settings.docling_cpu_threads
        self.table_mode = settings.docling_table_mode
        self.ocr_bitmap_threshold = settings.docling_ocr_bitmap_threshold
        self.lock = Lock()
        logger.info(
            "[Docling] initialization=%.3fs device=cpu threads=%d table_mode=%s "
            "ocr=auto ocr_bitmap_threshold=%.2f page_images=false",
            self.initialization_seconds,
            self.cpu_threads,
            self.table_mode,
            self.ocr_bitmap_threshold,
        )

    def convert(self, input_path: Path, result_dir: Path, output_stem: str) -> ConversionArtifacts:
        started = time.perf_counter()
        conversion_started = time.perf_counter()
        conversion = self._converter.convert(input_path)
        conversion_seconds = time.perf_counter() - conversion_started
        document = conversion.document
        assets_dir = result_dir / "assets"
        assets_dir.mkdir()

        asset_started = time.perf_counter()
        tables = 0
        for item, _level in document.iterate_items():
            if isinstance(item, TableItem):
                image = item.get_image(document)
                if image is not None:
                    tables += 1
                    image.save(assets_dir / f"table-{tables:03d}.png", "PNG")
        table_asset_seconds = time.perf_counter() - asset_started

        markdown_started = time.perf_counter()
        generated_md = result_dir / f"{output_stem}.md"
        document.save_as_markdown(
            generated_md,
            artifacts_dir=Path("assets"),
            image_mode=ImageRefMode.REFERENCED,
        )
        markdown = generated_md.read_text(encoding="utf-8")
        markdown, figures = _normalize_picture_names(markdown, assets_dir)
        generated_md.write_text(markdown, encoding="utf-8")
        markdown_seconds = time.perf_counter() - markdown_started

        if not any(assets_dir.iterdir()):
            assets_dir.rmdir()

        zip_started = time.perf_counter()
        zip_path = result_dir / f"{output_stem}-docling.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(generated_md, generated_md.name)
            if assets_dir.exists():
                for asset in sorted(assets_dir.iterdir()):
                    archive.write(asset, f"assets/{asset.name}")
        zip_seconds = time.perf_counter() - zip_started

        pages = len(document.pages) if document.pages else None
        total_seconds = time.perf_counter() - started
        internal_timings = _docling_timings(conversion.timings)
        phase_timings = {
            "conversion": conversion_seconds,
            "table_asset_export": table_asset_seconds,
            "markdown_figure_export": markdown_seconds,
            "zip_generation": zip_seconds,
            "total": total_seconds,
            **{f"docling_{name}": value for name, value in internal_timings.items()},
        }
        logger.info("[Docling] file=%s pages=%s", input_path.name, pages or "unknown")
        logger.info(
            "[Docling] conversion=%.3fs table_asset_export=%.3fs "
            "markdown_figure_export=%.3fs zip_generation=%.3fs total=%.3fs",
            conversion_seconds,
            table_asset_seconds,
            markdown_seconds,
            zip_seconds,
            total_seconds,
        )
        for name, seconds in internal_timings.items():
            logger.info("[Docling] stage_%s=%.3fs", name, seconds)
        return ConversionArtifacts(
            markdown=markdown,
            markdown_path=generated_md,
            zip_path=zip_path,
            pages=pages,
            processing_seconds=round(total_seconds, 2),
            figures=figures,
            table_images=tables,
            timings=phase_timings,
        )


def _normalize_picture_names(markdown: str, assets_dir: Path) -> tuple[str, int]:
    """Replace Docling hash filenames with stable figure-NNN names."""
    images = sorted(assets_dir.glob("image_*.png"))
    for index, image in enumerate(images, start=1):
        target = assets_dir / f"figure-{index:03d}.png"
        markdown = markdown.replace(image.name, target.name)
        image.replace(target)
    return markdown.replace("\\", "/"), len(images)


def _docling_timings(timings: dict[str, Any]) -> dict[str, float]:
    measured: dict[str, float] = {}
    for name, item in timings.items():
        values = getattr(item, "times", None)
        if values:
            measured[name] = float(sum(values))
    return measured
