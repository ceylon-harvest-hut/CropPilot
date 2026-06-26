from __future__ import annotations

import socket
import ssl
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.domains.ingestion.content import ExtractOptions, RawContent
from app.domains.ingestion.extractor import ContentExtractor
from app.domains.ingestion.source_types import SOURCE_TYPE_WEB_URL

DEFAULT_TIMEOUT_SECONDS = 30
USER_AGENT = "CropPilot/1.0"

_DEFAULT_OPTIONS = ExtractOptions()


class HttpExtractor(ContentExtractor):
    """Fetch any HTTP(S) resource into memory.

    Unlike the old ``web_fetch``, binary responses (PDF, DOCX, …) are allowed;
    the loader stack decides whether it can parse the returned media type.
    """

    name = "http"

    def supports(self, source_uri: str, source_type: str) -> bool:
        if source_type != SOURCE_TYPE_WEB_URL:
            return False
        parsed = urlparse(source_uri)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def extract(
        self,
        source_uri: str,
        source_type: str,
        options: ExtractOptions | None = None,
    ) -> RawContent:
        opts = options or _DEFAULT_OPTIONS
        timeout = opts.timeout_seconds
        request = Request(source_uri, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(
                request,
                timeout=timeout,
                context=ssl.create_default_context(),
            ) as response:
                final_url = response.geturl()
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
                raw = response.read(opts.max_bytes + 1)
        except HTTPError as exc:
            raise ValueError(f"HTTP error {exc.code} fetching URL: {source_uri}") from exc
        except TimeoutError as exc:
            raise ValueError(
                f"Request timed out after {timeout}s fetching URL: {source_uri}"
            ) from exc
        except socket.timeout as exc:
            raise ValueError(
                f"Request timed out after {timeout}s fetching URL: {source_uri}"
            ) from exc
        except URLError as exc:
            if _is_timeout(exc.reason):
                raise ValueError(
                    f"Request timed out after {timeout}s fetching URL: {source_uri}"
                ) from exc
            raise ValueError(f"Failed to fetch URL: {source_uri}") from exc

        if len(raw) > opts.max_bytes:
            raise ValueError(f"Response too large (>{opts.max_bytes} bytes): {source_uri}")

        if not raw.strip():
            raise ValueError(f"No content fetched from URL: {source_uri}")

        persisted_path: Path | None = None
        if opts.persist_raw and opts.raw_output_path is not None:
            opts.raw_output_path.parent.mkdir(parents=True, exist_ok=True)
            opts.raw_output_path.write_bytes(raw)
            persisted_path = opts.raw_output_path

        return RawContent(
            source_uri=source_uri,
            resolved_uri=final_url,
            source_type=source_type,
            media_type=content_type,
            data=raw,
            charset=charset,
            local_path=None,
            persisted_path=persisted_path,
        )


def _is_timeout(reason: object) -> bool:
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(reason).lower()
