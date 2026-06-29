from __future__ import annotations

from app.shared.document.content import RawContent
from app.shared.document.loader import DocumentLoader
from app.shared.document.source_types import validate_source_uri_shape


class LoaderValidationError(Exception):
    def __init__(self, message: str, **context: object) -> None:
        self.message = message
        self.context = context
        super().__init__(message)

    def as_detail(self) -> dict[str, object]:
        return {"message": self.message, **self.context}


def validate_source_uri_for_type(source_uri: str, source_type: str) -> None:
    """Validate that the URI shape matches the declared source type.

    Raises ``ValueError`` on mismatch (e.g. file path with ``web_url`` type).
    """
    validate_source_uri_shape(source_uri, source_type)


def validate_loader_selection(
    loader: DocumentLoader,
    raw: RawContent,
    all_loaders: list[DocumentLoader] | None = None,
) -> None:
    """Raise LoaderValidationError when *loader* cannot handle *raw*."""
    if loader.supports(raw):
        return

    allowed_loaders = (
        [l.name for l in all_loaders if l.supports(raw)]
        if all_loaders
        else []
    )

    supported_types = loader.supported_media_types()
    supported_exts = loader.supported_extensions()

    details: dict[str, object] = {
        "loader": loader.name,
        "media_type": raw.media_type,
        "allowed_loaders": allowed_loaders,
    }
    if supported_types is not None:
        details["supported_media_types"] = sorted(supported_types)
    if supported_exts is not None:
        details["supported_extensions"] = sorted(supported_exts)

    raise LoaderValidationError(
        f"Loader {loader.name!r} does not support media type {raw.media_type!r}",
        **details,
    )
