from app.shared.document.loader import KnowledgeDocument
from app.domains.graph.text import prepare_extraction_text


def test_prepare_extraction_text_joins_documents() -> None:
    docs = [
        KnowledgeDocument("First part.", {"source_uri": "a.txt"}),
        KnowledgeDocument("Second part.", {"source_uri": "a.txt"}),
    ]
    text = prepare_extraction_text(docs)
    assert text == "First part.\n\nSecond part."


def test_prepare_extraction_text_empty_list() -> None:
    assert prepare_extraction_text([]) == ""
