from typing import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session

_engine_instance: Engine | None = None


def set_engine(engine: Engine) -> None:
    """由 main.py 启动时（或测试）注入 engine。"""
    global _engine_instance
    _engine_instance = engine


def get_engine() -> Engine | None:
    return _engine_instance


def get_session() -> Iterator[Session]:
    engine = _engine_instance
    if engine is None:
        raise RuntimeError("DB engine not initialized; call set_engine() first.")
    with Session(engine) as session:
        yield session
