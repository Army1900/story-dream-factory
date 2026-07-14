from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

# 确保所有模型被注册到 SQLModel.metadata
import app.models.world  # noqa: F401
import app.models.location  # noqa: F401
import app.models.character  # noqa: F401
import app.models.relationship  # noqa: F401
import app.models.event  # noqa: F401
import app.models.memory  # noqa: F401
import app.models.image_asset  # noqa: F401
import app.models.director  # noqa: F401


@pytest.fixture()
def memory_db_url() -> str:
    return "sqlite:///:memory:"


@pytest.fixture()
def session(memory_db_url):
    engine = create_engine(memory_db_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture()
def worlds_tmp(tmp_path, monkeypatch):
    """把 WORLDS_DIR 指向临时目录并创建。

    所有 API 模块运行时调用 ``get_settings()``（每次新建 Settings()），
    pydantic-settings 会读取环境变量，因此 setenv 对所有模块生效。
    """
    worlds = tmp_path / "worlds"
    worlds.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WORLDS_DIR", str(worlds))
    return worlds


@pytest.fixture()
def mock_llm(monkeypatch):
    """Mock LLM 网关，避免真实 API 调用。"""
    mock = MagicMock()
    mock.complete = AsyncMock(return_value="这是助手的回复。")
    mock.complete_json = AsyncMock(return_value={})

    def _get_llm():
        return mock

    monkeypatch.setattr("app.api.builder._get_llm", _get_llm)
    return mock


@pytest.fixture()
def client_fixture(tmp_path, worlds_tmp):
    from app.main import app

    with TestClient(app) as c:
        yield c
