import os

from fastapi import FastAPI

from app.api.deps import set_engine
from app.api.router import api_router
from app.config import get_settings
from app.persistence.db import create_db_engine, init_db

app = FastAPI(title="Story Dream Factory", version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    # 文件系统持久化：确保 worlds/ 目录存在
    os.makedirs(settings.worlds_dir, exist_ok=True)
    # 保留 DB init（向后兼容，过渡期不删）
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    set_engine(engine)
