import argparse
import json
import tempfile
import time
from pathlib import Path

from docling_api.config import Settings
from docling_api.models import ConversionOptions
from docling_api.orchestrator import UnifiedConverter


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke benchmark unified conversion routing.")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    reports = []
    with tempfile.TemporaryDirectory(prefix="unified-benchmark-") as temporary:
        root = Path(temporary)
        engine = UnifiedConverter(Settings(temp_directory=root / "state"))
        for index, source in enumerate(args.files):
            result_dir = root / f"result-{index}"
            result_dir.mkdir()
            started = time.perf_counter()
            result = engine.convert(
                source.resolve(), result_dir, source.stem, ConversionOptions(images="ignore")
            )
            elapsed = time.perf_counter() - started
            reports.append(
                {
                    "file": source.name,
                    "engine": result.engine,
                    "pages": result.pages,
                    "total_seconds": round(elapsed, 3),
                    "seconds_per_page": round(elapsed / max(result.pages or 1, 1), 3),
                    "fallback": result.fallback_reason,
                    "cache_hit": result.cache_hit,
                    "markdown_characters": len(result.markdown),
                }
            )
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
