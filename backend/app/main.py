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
    engine = create_db_engine(settings.database_url)
    init_db(engine)
    set_engine(engine)
