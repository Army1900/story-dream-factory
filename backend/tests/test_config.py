import os


def test_config_reads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/test.db")
    monkeypatch.setenv("IMAGE_STORAGE_PATH", "./data/images")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setenv("LLM_TIER1_MODEL", "openai/glm-4-plus")

    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./data/test.db"
    assert settings.image_storage_path == "./data/images"
    assert settings.zhipu_api_key == "test-key"
    assert settings.llm_tier1_model == "openai/glm-4-plus"


def test_config_has_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./data/story.db"
