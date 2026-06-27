from app.domains.inference.data import RetrievedChunk
from app.domains.inference.references import build_rag_context, reference_title


def test_reference_title_prefers_crop_name() -> None:
    assert reference_title("Pepper", "https://dea.gov.lk/pepper/") == "Pepper"


def test_reference_title_from_url_slug() -> None:
    assert reference_title("", "https://dea.gov.lk/lemon-grass/") == "Lemon Grass"


def test_build_rag_context_groups_by_source_uri() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            text_content="Variety details here.",
            section_name="Varieties",
            crop_tag="Pepper",
            source_uri="https://dea.gov.lk/pepper/",
        ),
        RetrievedChunk(
            chunk_id="c2",
            text_content="History of pepper cultivation.",
            section_name="History",
            crop_tag="Pepper",
            source_uri="https://dea.gov.lk/pepper/",
        ),
        RetrievedChunk(
            chunk_id="c3",
            text_content="Cocoa growing areas.",
            section_name="Major Growing Areas",
            crop_tag="Cocoa",
            source_uri="https://dea.gov.lk/cocoa/",
        ),
    ]

    context, references = build_rag_context(chunks)

    assert len(references) == 2
    assert references[0].source_uri == "https://dea.gov.lk/pepper/"
    assert references[0].title == "Pepper"
    assert references[0].source_type == "web_url"
    assert references[1].title == "Cocoa"

    assert "--- Pepper ---" in context
    assert "Source: https://dea.gov.lk/pepper/" in context
    assert "### Varieties" in context
    assert "--- Cocoa ---" in context


def test_build_rag_context_empty() -> None:
    context, references = build_rag_context([])
    assert context == ""
    assert references == []
