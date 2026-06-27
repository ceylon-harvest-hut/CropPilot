from unittest.mock import MagicMock

from app.domains.inference.data import AnswerResult, RetrievedChunk
from app.domains.inference.service import InferenceService


def _make_chunk(n: int, source_uri: str = "https://dea.gov.lk/pepper/") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{n}",
        text_content=f"Content about pepper number {n}.",
        section_name="Introduction",
        crop_tag="Pepper",
        source_uri=source_uri,
    )


def test_ask_returns_answer_result() -> None:
    retriever = MagicMock()
    chunks = [_make_chunk(1), _make_chunk(2)]
    retriever.search.return_value = chunks

    llm = MagicMock()
    llm.generate.return_value = "Pepper is a tropical spice grown widely in Sri Lanka."

    service = InferenceService(retriever=retriever, llm=llm)
    result = service.ask("What is pepper?", crop_tag="Pepper")

    assert isinstance(result, AnswerResult)
    assert result.text == "Pepper is a tropical spice grown widely in Sri Lanka."
    assert len(result.references) == 1
    assert result.references[0].source_uri == "https://dea.gov.lk/pepper/"


def test_ask_passes_labeled_context_to_llm() -> None:
    retriever = MagicMock()
    retriever.search.return_value = [
        RetrievedChunk(
            chunk_id="c1",
            text_content="First chunk.",
            section_name="Intro",
            crop_tag="Pepper",
            source_uri="https://dea.gov.lk/pepper/",
        ),
        RetrievedChunk(
            chunk_id="c2",
            text_content="Second chunk.",
            section_name="Cultivation",
            crop_tag="Pepper",
            source_uri="https://dea.gov.lk/cocoa/",
        ),
    ]

    llm = MagicMock()
    llm.generate.return_value = "Answer here."

    service = InferenceService(retriever=retriever, llm=llm)
    service.ask("Tell me about pepper.", crop_tag="Pepper")

    context = llm.generate.call_args[0][1]
    assert "--- Pepper ---" in context
    assert "Source: https://dea.gov.lk/pepper/" in context
    assert "### Intro" in context
    assert "First chunk." in context
    assert "--- Pepper ---" in context or "--- Cocoa ---" in context
    assert "Source: https://dea.gov.lk/cocoa/" in context


def test_ask_calls_retriever_with_crop_tag() -> None:
    retriever = MagicMock()
    retriever.search.return_value = []

    llm = MagicMock()
    llm.generate.return_value = ""

    service = InferenceService(retriever=retriever, llm=llm)
    service.ask("question", crop_tag="Pepper")

    retriever.search.assert_called_once_with("question", crop_tag="Pepper", k=3)
    llm.generate.assert_called_once()
    assert llm.generate.call_args[1]["template"] == "context_only"


def test_ask_passes_template_to_llm() -> None:
    retriever = MagicMock()
    retriever.search.return_value = []

    llm = MagicMock()
    llm.generate.return_value = "Hybrid answer."

    service = InferenceService(retriever=retriever, llm=llm)
    service.ask("question", template="hybrid")

    llm.generate.assert_called_once()
    assert llm.generate.call_args[1]["template"] == "hybrid"
