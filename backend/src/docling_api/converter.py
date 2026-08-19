import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, TableItem


@dataclass(frozen=True)
class ConversionArtifacts:
    markdown: str
    markdown_path: Path
    zip_path: Path
    pages: int | None
    processing_seconds: float
    figures: int
    table_images: int


class DoclingEngine:
    """One reusable converter protected by a single-conversion lock."""

    def __init__(self) -> None:
        options = PdfPipelineOptions()
        options.generate_picture_images = True
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        self.lock = Lock()

    def convert(self, input_path: Path, result_dir: Path, output_stem: str) -> ConversionArtifacts:
        started = time.perf_counter()
        conversion = self._converter.convert(input_path)
        document = conversion.document
        assets_dir = result_dir / "assets"
        assets_dir.mkdir()

        tables = 0
        for item, _level in document.iterate_items():
            if isinstance(item, TableItem):
                image = item.get_image(document)
                if image is not None:
                    tables += 1
                    image.save(assets_dir / f"table-{tables:03d}.png", "PNG")

        generated_md = result_dir / f"{output_stem}.md"
        document.save_as_markdown(
            generated_md,
            artifacts_dir=Path("assets"),
            image_mode=ImageRefMode.REFERENCED,
        )
        markdown = generated_md.read_text(encoding="utf-8")
        markdown, figures = _normalize_picture_names(markdown, assets_dir)
        generated_md.write_text(markdown, encoding="utf-8")

        if not any(assets_dir.iterdir()):
            assets_dir.rmdir()

        zip_path = result_dir / f"{output_stem}-docling.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(generated_md, generated_md.name)
            if assets_dir.exists():
                for asset in sorted(assets_dir.iterdir()):
                    archive.write(asset, f"assets/{asset.name}")

        pages = len(document.pages) if document.pages else None
        return ConversionArtifacts(
            markdown=markdown,
            markdown_path=generated_md,
            zip_path=zip_path,
            pages=pages,
            processing_seconds=round(time.perf_counter() - started, 2),
            figures=figures,
            table_images=tables,
        )


def _normalize_picture_names(markdown: str, assets_dir: Path) -> tuple[str, int]:
    """Replace Docling hash filenames with stable figure-NNN names."""
    images = sorted(assets_dir.glob("image_*.png"))
    for index, image in enumerate(images, start=1):
        target = assets_dir / f"figure-{index:03d}.png"
        markdown = markdown.replace(image.name, target.name)
        image.replace(target)
    return markdown.replace("\\", "/"), len(images)
