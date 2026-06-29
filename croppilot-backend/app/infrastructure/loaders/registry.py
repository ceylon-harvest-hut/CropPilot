from __future__ import annotations

from app.shared.document.content import RawContent
from app.shared.document.loader import DocumentLoader
from app.infrastructure.loaders.dea_gov_lk_loader import DeaGovLkLoader
from app.infrastructure.loaders.dea_gov_lk_si_loader import DeaGovLkSiLoader
from app.infrastructure.loaders.doa_hordi_loader import DoaHordiLoader
from app.infrastructure.loaders.docling_loader import DoclingLoader
from app.infrastructure.loaders.html_plain_loader import HtmlPlainLoader
from app.infrastructure.loaders.text_loader import TextLoader
from app.infrastructure.loaders.validation import LoaderValidationError, validate_loader_selection


def build_all_loaders() -> list[DocumentLoader]:
    return [
        TextLoader(),
        DoclingLoader(),
        HtmlPlainLoader(),
        DeaGovLkLoader(),
        DeaGovLkSiLoader(),
        DoaHordiLoader(),
    ]


class DocumentLoaderRegistry:
    def __init__(self, loaders: list[DocumentLoader]) -> None:
        self._loaders_by_name = {loader.name: loader for loader in loaders}

    def resolve(self, loader_name: str, raw: RawContent) -> DocumentLoader:
        loader = self._loaders_by_name.get(loader_name)
        if loader is None:
            known = ", ".join(sorted(self._loaders_by_name))
            raise ValueError(f"Unknown loader: {loader_name!r}. Available: {known}")
        validate_loader_selection(loader, raw, list(self._loaders_by_name.values()))
        return loader
