from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from App.api import __version__
from App.api.config import CORS_ORIGINS
from App.api.routers import documents, health, projects
from App.dao.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ratgp.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("RATGP API 就绪，CORS 允许：%s", ", ".join(CORS_ORIGINS))
    yield


app = FastAPI(
    title="RATGP API",
    description="需求解析与测试用例辅助生成平台 —— 后端接口",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(documents.router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": "RATGP API", "version": __version__, "docs": "/docs"}
