from __future__ import annotations

from app.domains.ingestion.loader import DocumentLoader
from app.domains.ingestion.source_types import validate_source_uri_shape
from app.infrastructure.loaders.catalog import loaders_for_source_type


class LoaderValidationError(Exception):
    def __init__(self, message: str, **context: object) -> None:
        self.message = message
        self.context = context
        super().__init__(message)

    def as_detail(self) -> dict[str, object]:
        return {"message": self.message, **self.context}


def validate_loader_selection(
    loader: DocumentLoader,
    source_uri: str,
    source_type: str,
) -> None:
    validate_source_uri_shape(source_uri, source_type)

    if source_type not in loader.supported_source_types():
        allowed_loaders = loaders_for_source_type(source_type)
        raise LoaderValidationError(
            f"Loader {loader.name!r} does not support source_type {source_type!r}",
            loader=loader.name,
            source_type=source_type,
            allowed_loaders=allowed_loaders,
        )

    if not loader.supports(source_uri, source_type):
        raise LoaderValidationError(
            f"Loader {loader.name!r} cannot load source_uri for source_type {source_type!r}",
            loader=loader.name,
            source_type=source_type,
            source_uri=source_uri,
        )
