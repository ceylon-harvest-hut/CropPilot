from unittest.mock import MagicMock

from app.domains.inference.data import AnswerResult, RetrievedChunk
from app.domains.inference.service import InferenceService


def _make_chunk(n: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{n}",
        text_content=f"Content about pepper number {n}.",
        section_name="Introduction",
        crop_tag="Pepper",
    )


def test_ask_returns_answer_result() -> None:
    retriever = MagicMock()
    chunks = [_make_chunk(1), _make_chunk(2)]
    retriever.search.return_value = chunks

    llm = MagicMock()
    llm.generate.return_value = "Pepper is a tropical spice."

    service = InferenceService(retriever=retriever, llm=llm)
    result = service.ask("What is pepper?", crop_tag="Pepper")

    assert isinstance(result, AnswerResult)
    assert result.text == "Pepper is a tropical spice."
    assert result.sources == chunks


def test_ask_passes_context_to_llm() -> None:
    retriever = MagicMock()
    retriever.search.return_value = [
        RetrievedChunk(
            chunk_id="c1",
            text_content="First chunk.",
            section_name="Intro",
            crop_tag="Pepper",
        ),
        RetrievedChunk(
            chunk_id="c2",
            text_content="Second chunk.",
            section_name="Cultivation",
            crop_tag="Pepper",
        ),
    ]

    llm = MagicMock()
    llm.generate.return_value = "Answer here."

    service = InferenceService(retriever=retriever, llm=llm)
    service.ask("Tell me about pepper.", crop_tag="Pepper")

    llm.generate.assert_called_once_with(
        "Tell me about pepper.", "First chunk.\n\nSecond chunk."
    )


def test_ask_calls_retriever_with_crop_tag() -> None:
    retriever = MagicMock()
    retriever.search.return_value = []

    llm = MagicMock()
    llm.generate.return_value = ""

    service = InferenceService(retriever=retriever, llm=llm)
    service.ask("question", crop_tag="Pepper")

    retriever.search.assert_called_once_with("question", crop_tag="Pepper")
