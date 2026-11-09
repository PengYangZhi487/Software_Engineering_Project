from __future__ import annotations

from fastapi import APIRouter

from App.api import __version__
from App.api import repository
from App.api.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthOut, summary="健康检查")
def health() -> HealthOut:
    """前端启动时先打这个接口，能同时确认 API 与数据库是否可用。"""
    try:
        projects = len(repository.list_projects())
        return HealthOut(status="ok", db="ok", projects=projects, version=__version__)
    except Exception:  # pragma: no cover - 只在数据库不可用时触发
        return HealthOut(status="degraded", db="error", projects=None, version=__version__)
