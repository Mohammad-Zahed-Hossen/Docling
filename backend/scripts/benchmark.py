import argparse
import json
import logging
import tempfile
import time
from pathlib import Path
from zipfile import ZipFile

import pypdfium2 as pdfium

from docling_api.config import get_settings
from docling_api.converter import DoclingEngine


def inspect_pdf(path: Path) -> tuple[int, int]:
    document = pdfium.PdfDocument(path)
    text_characters = 0
    try:
        for page in document:
            text_page = page.get_textpage()
            text_characters += len(text_page.get_text_range().strip())
            text_page.close()
            page.close()
        return len(document), text_characters
    finally:
        document.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the production Docling conversion engine."
    )
    parser.add_argument("pdf", type=Path, help="Path to a local PDF")
    args = parser.parse_args()
    source = args.pdf.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        parser.error("pdf must point to an existing PDF file")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pages, text_characters = inspect_pdf(source)
    with tempfile.TemporaryDirectory(prefix="docling-benchmark-") as temporary:
        root = Path(temporary)
        cold_dir = root / "cold"
        warm_dir = root / "warm"
        cold_dir.mkdir()
        warm_dir.mkdir()

        initialization_started = time.perf_counter()
        engine = DoclingEngine(get_settings())
        initialization_seconds = time.perf_counter() - initialization_started

        cold_started = time.perf_counter()
        cold = engine.convert(source, cold_dir, "benchmark-cold")
        cold_conversion_seconds = time.perf_counter() - cold_started

        warm_started = time.perf_counter()
        warm = engine.convert(source, warm_dir, "benchmark-warm")
        warm_seconds = time.perf_counter() - warm_started
        with ZipFile(warm.zip_path) as package:
            zip_entries = package.namelist()

        report = {
            "file": str(source),
            "file_bytes": source.stat().st_size,
            "pages": pages,
            "selectable_text_characters": text_characters,
            "has_selectable_text": text_characters > 0,
            "ocr_configured": "automatic_pdf_aware",
            "ocr_bitmap_area_threshold": engine.ocr_bitmap_threshold,
            "ocr_used": warm.timings.get("docling_ocr", 0.0) > 0.05,
            "warm_ocr_seconds": round(warm.timings.get("docling_ocr", 0.0), 3),
            "cpu_threads": engine.cpu_threads,
            "table_mode": engine.table_mode,
            "initialization_seconds": round(initialization_seconds, 3),
            "cold_conversion_seconds": round(cold_conversion_seconds, 3),
            "cold_start_total_seconds": round(initialization_seconds + cold_conversion_seconds, 3),
            "warm_conversion_seconds": round(warm_seconds, 3),
            "warm_seconds_per_page": round(warm_seconds / max(pages, 1), 3),
            "figures": warm.figures,
            "table_images": warm.table_images,
            "markdown_identical_cold_warm": cold.markdown == warm.markdown,
            "zip_entries": zip_entries,
            "relative_asset_references": "assets/" in warm.markdown or warm.figures == 0,
            "cold_phase_seconds": {key: round(value, 3) for key, value in cold.timings.items()},
            "warm_phase_seconds": {key: round(value, 3) for key, value in warm.timings.items()},
        }
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
