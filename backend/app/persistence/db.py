import os
from typing import Iterator

from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlmodel import Session, SQLModel, create_engine


def create_db_engine(database_url: str, echo: bool = False) -> Engine:
    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )
    _ensure_sqlite_parent_dir(database_url)
    return create_engine(database_url, echo=echo, connect_args=connect_args)


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """对于文件型 SQLite URL，确保父目录存在（:memory: 与非 sqlite 跳过）。"""
    if not database_url.startswith("sqlite"):
        return
    database = make_url(database_url).database
    if not database or database == ":memory:":
        return
    parent = os.path.dirname(database)
    if parent:
        os.makedirs(parent, exist_ok=True)


def init_db(engine: Engine) -> None:
    """创建所有表。需先 import 所有模型模块以注册到 metadata。"""
    import app.models.world  # noqa: F401
    import app.models.location  # noqa: F401
    import app.models.character  # noqa: F401
    import app.models.relationship  # noqa: F401
    import app.models.event  # noqa: F401
    import app.models.memory  # noqa: F401
    import app.models.image_asset  # noqa: F401
    import app.models.director  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session(engine: Engine) -> Iterator[Session]:
    """FastAPI 依赖：返回 session 生成器。"""
    with Session(engine) as session:
        yield session
