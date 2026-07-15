import os

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings

app = FastAPI(title="Story Dream Factory", version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    # 文件系统持久化：确保 worlds/ 目录存在
    os.makedirs(settings.worlds_dir, exist_ok=True)
    # DB 层（db.py / repository.py / deps.py）保留代码但不再启动初始化——
    # 系统已全面切换到一世界一目录的 YAML 持久化。
