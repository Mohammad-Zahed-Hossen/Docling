import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .config import Settings
from .models import WebExtractionResult
from .web_fetcher import WebError, fetch_url

IMAGE_RE = re.compile(r"!\[([^]]*)]\((?:<)?([^\s)>]+)(?:>)?(?:\s+['\"][^'\"]*['\"])?\)")
LOW_VALUE = re.compile(r"(?:logo|avatar|favicon|icon|emoji|pixel|tracking|badge|advert|social)", re.I)


class WebExtractor:
    version = "defuddle-0.19.2-v1"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.runner = Path(__file__).resolve().parents[3] / "frontend" / "scripts" / "defuddle.mjs"

    def extract(self, html: bytes, source_url: str, result_dir: Path, images: str) -> WebExtractionResult:
        if not self.runner.is_file():
            raise WebError(500, "WEB_EXTRACTION_FAILED", "The local web extractor is not installed.")
        payload = json.dumps(
            {"html": html.decode("utf-8", errors="replace"), "url": source_url, "images": images}
        )
        try:
            process = subprocess.run(
                ["node", str(self.runner)],
                input=payload,
                text=True,
                capture_output=True,
                timeout=self.settings.web_total_timeout_seconds,
                check=False,
                encoding="utf-8",
            )
        except (OSError, subprocess.TimeoutExpired):
            raise WebError(500, "WEB_EXTRACTION_FAILED", "Readable content could not be extracted from this page.") from None
        if process.returncode != 0:
            raise WebError(422, "WEB_EXTRACTION_FAILED", "Readable content could not be extracted from this page.")
        try:
            data = json.loads(process.stdout)
        except json.JSONDecodeError:
            raise WebError(500, "WEB_EXTRACTION_FAILED", "Readable content could not be extracted from this page.") from None
        markdown = str(data.get("content") or "").strip()
        plain = re.sub(r"\W+", "", markdown)
        if len(plain) < 80:
            raise WebError(
                422,
                "WEB_EXTRACTION_FAILED",
                "This page requires login or browser rendering and cannot be reliably extracted in lightweight mode.",
            )
        warnings: list[str] = []
        if images == "extract":
            markdown, warnings = self._preserve_images(markdown, source_url, result_dir)
        else:
            markdown = IMAGE_RE.sub("", markdown)
        return WebExtractionResult(
            title=_clean_optional(data.get("title")),
            markdown=markdown,
            source_url=source_url,
            author=_clean_optional(data.get("author")),
            published_at=_clean_optional(data.get("published")),
            warnings=warnings,
        )

    def _preserve_images(self, markdown: str, source_url: str, result_dir: Path) -> tuple[str, list[str]]:
        candidates: list[tuple[str, str]] = []
        for alt, raw_url in IMAGE_RE.findall(markdown):
            absolute = urljoin(source_url, raw_url)
            if (
                urlsplit(absolute).scheme in {"http", "https"}
                and not LOW_VALUE.search(f"{alt} {absolute}")
                and (alt, absolute) not in candidates
            ):
                candidates.append((alt, absolute))
        candidates = candidates[: self.settings.max_web_images]
        if not candidates:
            return markdown, []
        assets = result_dir / "assets"
        assets.mkdir(exist_ok=True)
        replacements: dict[str, str] = {}
        warnings: list[str] = []
        with ThreadPoolExecutor(max_workers=min(4, len(candidates))) as pool:
            futures = {pool.submit(fetch_url, url, self.settings, image=True): (alt, url, index) for index, (alt, url) in enumerate(candidates, 1)}
            for future in as_completed(futures):
                alt, url, index = futures[future]
                try:
                    fetched = future.result()
                    extension = _image_extension(fetched.content_type)
                    name = f"figure-{index:03d}{extension}"
                    (assets / name).write_bytes(fetched.content)
                    replacements[url] = f"assets/{name}"
                except WebError:
                    warnings.append(f"Could not preserve webpage image {index}; the remote reference was retained.")
        if not any(assets.iterdir()):
            assets.rmdir()
        def replace(match: re.Match[str]) -> str:
            alt, raw_url = match.group(1), match.group(2)
            absolute = urljoin(source_url, raw_url)
            return f"![{alt}]({replacements.get(absolute, absolute)})"
        return IMAGE_RE.sub(replace, markdown), warnings


def _clean_optional(value: object) -> str | None:
    cleaned = str(value).strip() if value else ""
    return cleaned or None


def _image_extension(content_type: str) -> str:
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(content_type, ".img")
