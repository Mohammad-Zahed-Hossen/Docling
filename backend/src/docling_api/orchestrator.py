import hashlib
import json
import logging
import re
import shutil
import time
import zipfile
from pathlib import Path
from threading import Lock

from .config import Settings
from .converter import DoclingEngine
from .engines import DoclingAdapter, MarkItDownEngine, PyMuPDFEngine, normalize_assets
from .inspector import inspect_pdf
from .markdown import canonicalize, quality_issues, validate
from .models import ConversionOptions, DocumentProfile, UnifiedResult

logger = logging.getLogger("docling_api.performance")
PDF = ".pdf"


class UnifiedConverter:
    def __init__(self, settings: Settings, docling: DoclingEngine | None = None) -> None:
        self.settings = settings
        self.lock = Lock()
        self._docling = DoclingAdapter(docling) if docling else None
        self._pymupdf = PyMuPDFEngine()
        self._markitdown: MarkItDownEngine | None = None
        self.cache_root = settings.temp_directory / "cache"
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def convert(
        self, input_path: Path, result_dir: Path, output_stem: str, options: ConversionOptions
    ) -> UnifiedResult:
        started = time.perf_counter()
        suffix = input_path.suffix.lower()
        profile: DocumentProfile | None = None
        inspection_seconds = 0.0
        if suffix == PDF:
            profile, inspection_seconds = inspect_pdf(input_path)
        engine_name, reason = self._route(suffix, options, profile)
        key = self._cache_key(input_path, options, engine_name)
        if options.cache and self._restore_cache(key, result_dir):
            return self._read_cached(result_dir, output_stem, started, engine_name, reason)

        engine = self._engine(engine_name)
        conversion_started = time.perf_counter()
        result = engine.convert(input_path, result_dir, options)
        conversion_seconds = time.perf_counter() - conversion_started
        fallback_reason = None
        if options.images == "ignore":
            shutil.rmtree(result_dir / "assets", ignore_errors=True)
            result.markdown = re.sub(
                r"^!\[[^]]*]\([^)]*\)\s*$", "", result.markdown, flags=re.MULTILINE
            )
        normalized = canonicalize(result.markdown)
        issues = quality_issues(normalized, result.pages or (profile.pages if profile else None))
        if (
            engine_name == "pymupdf4llm"
            and options.engine == "auto"
            and options.mode == "balanced"
            and issues
        ):
            fallback_reason = "; ".join(issues)
            shutil.rmtree(result_dir / "assets", ignore_errors=True)
            engine_name = "docling"
            reason = f"Fast extraction failed the quality gate: {fallback_reason}."
            result = self._engine("docling").convert(input_path, result_dir, options)
            normalized = canonicalize(result.markdown)

        normalized, figures, tables = normalize_assets(normalized, result_dir)
        normalized, validation_warnings = validate(normalized, result_dir)
        warnings = [*result.warnings, *validation_warnings]
        if options.image_descriptions != "off":
            warnings.append("Local image descriptions are not configured; captions were preserved.")
        markdown_path = result_dir / f"{output_stem}.md"
        markdown_path.write_text(normalized, encoding="utf-8")
        package_path = result_dir / f"{output_stem}.zip"
        self._package(markdown_path, result_dir / "assets", package_path)
        self._write_manifest(
            result_dir,
            engine_name,
            reason,
            result.pages,
            figures,
            tables,
            warnings,
            fallback_reason,
        )
        if options.cache:
            self._store_cache(key, result_dir)
        total = time.perf_counter() - started
        logger.info(
            "engine=%s pages=%s inspection=%.3fs conversion=%.3fs total=%.3fs fallback=%s",
            engine_name,
            result.pages,
            inspection_seconds,
            conversion_seconds,
            total,
            fallback_reason or "none",
        )
        return UnifiedResult(
            normalized,
            markdown_path,
            package_path,
            result.pages,
            round(total, 2),
            figures,
            tables,
            engine_name,
            reason,
            warnings,
            False,
            fallback_reason,
        )

    def _route(
        self, suffix: str, options: ConversionOptions, profile: DocumentProfile | None
    ) -> tuple[str, str]:
        if options.engine != "auto":
            if options.engine == "pymupdf4llm" and suffix != PDF:
                raise ValueError("PyMuPDF4LLM only supports PDF input.")
            if options.engine == "docling" and suffix != PDF:
                raise ValueError("Docling is configured for PDF input in V1.")
            return options.engine, "Selected manually."
        if suffix != PDF:
            return "markitdown", "Supported non-PDF format."
        assert profile is not None
        if options.ocr == "force":
            return "docling", "Forced OCR requires the accuracy engine."
        if options.mode == "fast":
            return "pymupdf4llm", "Fast mode uses the digital PDF path."
        if profile.difficult:
            return "docling", "Scanned or structurally complex PDF signals."
        return "pymupdf4llm", "Digital PDF with strong embedded text coverage."

    def _engine(self, name: str):
        if name == "docling":
            if self._docling is None:
                self._docling = DoclingAdapter(DoclingEngine(self.settings))
            return self._docling
        if name == "pymupdf4llm":
            return self._pymupdf
        if self._markitdown is None:
            self._markitdown = MarkItDownEngine()
        return self._markitdown

    def _cache_key(self, path: Path, options: ConversionOptions, engine: str) -> str:
        digest = hashlib.sha256(path.read_bytes())
        digest.update(
            json.dumps({**options.__dict__, "engine_result": engine}, sort_keys=True).encode()
        )
        return digest.hexdigest()

    def _restore_cache(self, key: str, result_dir: Path) -> bool:
        source = self.cache_root / key
        if not source.is_dir():
            return False
        shutil.copytree(source, result_dir, dirs_exist_ok=True)
        return True

    def _store_cache(self, key: str, result_dir: Path) -> None:
        target = self.cache_root / key
        if not target.exists():
            shutil.copytree(result_dir, target)

    def _read_cached(
        self, result_dir: Path, stem: str, started: float, engine: str, reason: str
    ) -> UnifiedResult:
        old_md = next(result_dir.glob("*.md"))
        md_path = result_dir / f"{stem}.md"
        old_md.rename(md_path)
        old_zip = next(result_dir.glob("*.zip"))
        zip_path = result_dir / f"{stem}.zip"
        old_zip.unlink()
        self._package(md_path, result_dir / "assets", zip_path)
        data = json.loads((result_dir / ".manifest.json").read_text(encoding="utf-8"))
        return UnifiedResult(
            md_path.read_text(encoding="utf-8"),
            md_path,
            zip_path,
            data["pages"],
            round(time.perf_counter() - started, 2),
            data["figures"],
            data["tables"],
            data.get("engine", engine),
            data.get("reason", reason),
            data.get("warnings", []),
            True,
            data.get("fallback_reason"),
        )

    @staticmethod
    def _package(markdown_path: Path, assets_dir: Path, package_path: Path) -> None:
        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(markdown_path, markdown_path.name)
            if assets_dir.exists():
                for asset in sorted(assets_dir.iterdir()):
                    archive.write(asset, f"assets/{asset.name}")

    @staticmethod
    def _write_manifest(
        result_dir: Path,
        engine: str,
        reason: str,
        pages: int | None,
        figures: int,
        tables: int,
        warnings: list[str],
        fallback_reason: str | None,
    ) -> None:
        data = {
            "engine": engine,
            "reason": reason,
            "pages": pages,
            "figures": figures,
            "tables": tables,
            "warnings": warnings,
            "fallback_reason": fallback_reason,
        }
        (result_dir / ".manifest.json").write_text(json.dumps(data), encoding="utf-8")
