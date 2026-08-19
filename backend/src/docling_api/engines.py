import re
import shutil
from pathlib import Path

from markitdown import MarkItDown

from .converter import DoclingEngine
from .models import ConversionOptions, EngineResult


class PyMuPDFEngine:
    name = "pymupdf4llm"

    def convert(self, input_path: Path, work_dir: Path, options: ConversionOptions) -> EngineResult:
        import pymupdf
        import pymupdf4llm

        assets_dir = work_dir / "assets"
        kwargs: dict[str, object] = {"show_progress": False}
        if options.images == "extract":
            assets_dir.mkdir(exist_ok=True)
            kwargs.update(write_images=True, image_path=str(assets_dir), image_format="png")
        markdown = pymupdf4llm.to_markdown(str(input_path), **kwargs)
        document = pymupdf.open(input_path)
        pages = len(document)
        document.close()
        assets = sorted(assets_dir.glob("*")) if assets_dir.exists() else []
        return EngineResult(markdown=markdown, pages=pages, assets=assets)


class MarkItDownEngine:
    name = "markitdown"

    def __init__(self) -> None:
        self._converter = MarkItDown(enable_plugins=False)

    def convert(
        self, input_path: Path, _work_dir: Path, _options: ConversionOptions
    ) -> EngineResult:
        result = self._converter.convert(str(input_path))
        return EngineResult(markdown=result.text_content)


class DoclingAdapter:
    name = "docling"

    def __init__(self, engine: DoclingEngine) -> None:
        self._engine = engine

    def convert(
        self, input_path: Path, work_dir: Path, _options: ConversionOptions
    ) -> EngineResult:
        raw = self._engine.convert(input_path, work_dir, "document")
        assets_dir = work_dir / "assets"
        assets = sorted(assets_dir.glob("*")) if assets_dir.exists() else []
        raw.markdown_path.unlink(missing_ok=True)
        raw.zip_path.unlink(missing_ok=True)
        return EngineResult(markdown=raw.markdown, pages=raw.pages, assets=assets)


def normalize_assets(markdown: str, result_dir: Path) -> tuple[str, int, int]:
    assets_dir = result_dir / "assets"
    if not assets_dir.exists():
        return markdown.replace("\\", "/"), 0, 0
    figures = tables = 0
    for source in sorted(p for p in assets_dir.iterdir() if p.is_file()):
        is_table = source.name.lower().startswith("table")
        if is_table:
            tables += 1
            target = assets_dir / f"table-{tables:03d}{source.suffix.lower()}"
        else:
            figures += 1
            target = assets_dir / f"figure-{figures:03d}{source.suffix.lower()}"
        if source != target:
            if target.exists():
                target.unlink()
            shutil.move(source, target)
        markdown = markdown.replace(source.name, target.name)
        markdown = re.sub(
            rf"(?<=\()(?:(?!\)).)*{re.escape(target.name)}(?=\))",
            f"assets/{target.name}",
            markdown,
        )
    if not any(assets_dir.iterdir()):
        assets_dir.rmdir()
    return markdown.replace("\\", "/"), figures, tables
