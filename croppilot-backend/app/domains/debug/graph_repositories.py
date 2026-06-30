from __future__ import annotations

from typing import Protocol

from app.domains.debug.graph_data import GraphCropDetail, GraphCropSummary


class GraphReadRepository(Protocol):
    def list_crop_summaries(self) -> list[GraphCropSummary]: ...

    def get_crop_detail(self, name: str) -> GraphCropDetail: ...
