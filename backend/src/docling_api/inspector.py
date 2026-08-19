import re
import time
from pathlib import Path

import pymupdf

from .models import DocumentProfile


def inspect_pdf(path: Path) -> tuple[DocumentProfile, float]:
    started = time.perf_counter()
    document = pymupdf.open(path)
    pages = len(document)
    text_pages = scanned_pages = image_count = table_signals = 0
    text_characters = 0
    column_pages = 0
    for page in document:
        text = page.get_text("text")
        count = len(text.strip())
        text_characters += count
        if count >= 80:
            text_pages += 1
        else:
            scanned_pages += 1
        images = page.get_images(full=True)
        image_count += len(images)
        blocks = page.get_text("blocks")
        if len(blocks) >= 10:
            column_pages += 1
        table_signals += len(re.findall(r"(?:\S+\s{2,}){2,}\S+", text))
    document.close()
    divisor = max(pages, 1)
    digital_ratio = text_pages / divisor
    scanned_ratio = scanned_pages / divisor
    image_density = min(1.0, image_count / divisor / 4)
    complexity = min(
        1.0,
        (column_pages / divisor) * 0.45
        + min(table_signals / divisor, 8) / 8 * 0.35
        + image_density * 0.2,
    )
    profile = DocumentProfile(
        pages=pages,
        text_characters=text_characters,
        digital_text_ratio=digital_ratio,
        scanned_page_ratio=scanned_ratio,
        image_density=image_density,
        table_signals=table_signals,
        layout_complexity=complexity,
        confidence=0.9 if pages else 0.0,
    )
    return profile, time.perf_counter() - started
