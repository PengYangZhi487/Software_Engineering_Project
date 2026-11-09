from __future__ import annotations

from fastapi import APIRouter

from App.api import repository
from App.api.schemas import ProjectOut

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut], summary="项目列表")
def list_projects() -> list[ProjectOut]:
    rows = repository.list_projects()
    return [
        ProjectOut(
            project_id=r["project_id"],
            project_name=r["project_name"],
            description=r["description"],
            req_count=r.get("req_count", 0),
        )
        for r in rows
    ]
