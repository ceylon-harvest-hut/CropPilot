from app.infrastructure.config import Settings, get_settings


def test_settings_defaults():
    settings = Settings()
    assert settings.embedding_backend == "fast"
    assert settings.default_chunker == "section"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()