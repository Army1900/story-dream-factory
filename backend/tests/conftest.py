import pytest
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
