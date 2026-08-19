import ipaddress
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from .config import Settings

USER_AGENT = "UnifiedMarkdownConverter/1.0 (+local public-webpage converter)"
DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


class WebError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code, self.code, self.message = status_code, code, message


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    content_type: str
    content: bytes
    document_suffix: str | None = None


def validate_public_url(raw_url: str) -> str:
    value = raw_url.strip()
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise WebError(422, "INVALID_URL", "Enter a valid public HTTP(S) URL.") from None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise WebError(422, "INVALID_URL", "Enter a valid public HTTP(S) URL.")
    if parsed.username or parsed.password:
        raise WebError(422, "INVALID_URL", "URLs containing credentials are not supported.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise WebError(403, "ACCESS_DENIED", "Local and private network URLs are not allowed.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, port or 443)}
    except socket.gaierror:
        raise WebError(400, "URL_FETCH_FAILED", "The webpage address could not be reached.") from None
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise WebError(403, "ACCESS_DENIED", "Local and private network URLs are not allowed.")
    netloc = host
    if ":" in host:
        netloc = f"[{host}]"
    if port:
        netloc += f":{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))


def fetch_url(url: str, settings: Settings, *, image: bool = False) -> FetchResult:
    current = validate_public_url(url)
    limit = settings.max_web_image_bytes if image else settings.max_webpage_bytes
    timeout = httpx.Timeout(
        settings.web_total_timeout_seconds, connect=settings.web_connect_timeout_seconds
    )
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
            for redirect_count in range(settings.web_redirect_limit + 1):
                with client.stream("GET", current, follow_redirects=False) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count >= settings.web_redirect_limit:
                            raise WebError(400, "URL_FETCH_FAILED", "The webpage redirected too many times.")
                        location = response.headers.get("location")
                        if not location:
                            raise WebError(400, "URL_FETCH_FAILED", "The webpage redirect was invalid.")
                        current = validate_public_url(urljoin(current, location))
                        continue
                    if response.status_code in {401, 403}:
                        raise WebError(403, "ACCESS_DENIED", "This page could not be accessed as public webpage content.")
                    if response.status_code >= 400:
                        raise WebError(400, "URL_FETCH_FAILED", "The webpage could not be fetched.")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    suffix = DOCUMENT_TYPES.get(content_type)
                    if image:
                        if not content_type.startswith("image/") or content_type == "image/svg+xml":
                            raise WebError(415, "UNSUPPORTED_WEB_CONTENT", "The image type is unsupported.")
                    elif not suffix and content_type not in {"text/html", "application/xhtml+xml"}:
                        raise WebError(415, "UNSUPPORTED_WEB_CONTENT", "The URL is not an HTML page or supported document.")
                    declared = response.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > limit:
                        raise WebError(413, "WEBPAGE_TOO_LARGE", "The webpage exceeds the configured size limit.")
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > limit:
                            raise WebError(413, "WEBPAGE_TOO_LARGE", "The webpage exceeds the configured size limit.")
                        chunks.append(chunk)
                    return FetchResult(current, content_type, b"".join(chunks), suffix)
    except WebError:
        raise
    except httpx.TimeoutException:
        raise WebError(408, "URL_TIMEOUT", "The webpage did not respond before the timeout.") from None
    except (httpx.HTTPError, OSError):
        raise WebError(400, "URL_FETCH_FAILED", "The webpage could not be fetched.") from None
    raise WebError(400, "URL_FETCH_FAILED", "The webpage could not be fetched.")


def write_direct_document(fetch: FetchResult, directory: Path) -> Path:
    assert fetch.document_suffix
    path = directory / f"download{fetch.document_suffix}"
    path.write_bytes(fetch.content)
    return path
