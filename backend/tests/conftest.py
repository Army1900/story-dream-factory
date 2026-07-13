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
def client_fixture(tmp_path):
    from app.api.deps import get_session, set_engine
    from app.main import app

    engine = create_engine(
        f"sqlite:///{tmp_path / 'builder.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    set_engine(engine)

    def _gs():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _gs
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
