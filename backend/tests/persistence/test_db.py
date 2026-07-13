from sqlmodel import Session, select

from app.models.world import World
from app.persistence.db import create_db_engine, init_db


def test_init_db_creates_all_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 't.db'}"
    engine = create_db_engine(url)
    init_db(engine)
    with Session(engine) as s:
        # 能插入并查询即说明建表成功
        s.add(World(name="x"))
        s.commit()
        rows = s.exec(select(World)).all()
        assert len(rows) == 1
        assert rows[0].name == "x"
    engine.dispose()


def test_create_db_engine_returns_engine():
    engine = create_db_engine("sqlite:///:memory:")
    assert engine is not None
    engine.dispose()
