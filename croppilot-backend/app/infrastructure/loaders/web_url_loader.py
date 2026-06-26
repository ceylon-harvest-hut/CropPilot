from __future__ import annotations

import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.domains.ingestion.source_types import SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.html_text import html_to_text

_DEFAULT_TIMEOUT_SECONDS = 30
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_USER_AGENT = "CropPilot/1.0"


def _timeout_message(source_uri: str) -> str:
    return (
        f"Request timed out after {_DEFAULT_TIMEOUT_SECONDS}s fetching URL: {source_uri}"
    )


def _is_timeout_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(exc).lower()


class WebUrlLoader(DocumentLoader):
    name = "web"

    def supported_source_types(self) -> frozenset[str]:
        return frozenset({SOURCE_TYPE_WEB_URL})

    def supports(self, source_uri: str, source_type: str) -> bool:
        if source_type != SOURCE_TYPE_WEB_URL:
            return False
        parsed = urlparse(source_uri)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def load(self, source_uri: str, source_type: str) -> list[KnowledgeDocument]:
        request = Request(source_uri, headers={"User-Agent": _USER_AGENT})
        try:
            with urlopen(
                request,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
                context=ssl.create_default_context(),
            ) as response:
                final_url = response.geturl()
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise ValueError(f"HTTP error {exc.code} fetching URL: {source_uri}") from exc
        except TimeoutError as exc:
            raise ValueError(_timeout_message(source_uri)) from exc
        except socket.timeout as exc:
            raise ValueError(_timeout_message(source_uri)) from exc
        except URLError as exc:
            if _is_timeout_error(exc.reason):
                raise ValueError(_timeout_message(source_uri)) from exc
            raise ValueError(f"Failed to fetch URL: {source_uri}") from exc

        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ValueError(f"Response too large (>{_MAX_RESPONSE_BYTES} bytes): {source_uri}")

        if content_type.startswith("text/") or "html" in content_type:
            html = raw.decode(charset, errors="replace")
            text = html_to_text(html) if "html" in content_type else html.strip()
            media_type = content_type
        else:
            raise ValueError(
                f"Unsupported web content type {content_type!r} for loader {self.name!r}"
            )

        if not text.strip():
            raise ValueError(f"No text content extracted from URL: {source_uri}")

        return [
            KnowledgeDocument(
                text=text,
                metadata={
                    "source_uri": source_uri,
                    "source_type": source_type,
                    "loader": self.name,
                    "media_type": media_type,
                    "final_url": final_url,
                },
            )
        ]
