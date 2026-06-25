from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LoadedDocument:
    text: str
    source_uri: str
    media_type: str


class DocumentLoader(Protocol):
    def supports(self, source_uri: str) -> bool: ...
    def load(self, source_uri: str) -> LoadedDocument: ...