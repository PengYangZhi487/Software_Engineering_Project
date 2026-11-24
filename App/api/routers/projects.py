"""项目：列表 / 新建 / 重命名 / 删除。

删除是「有保护的两段式」：项目下还有需求或文档时返回 409，调用方确认后
再带 ``force=true`` 重发，才会级联清理该项目全部子数据（含执行记录）。
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from App.api import repository
from App.api.schemas import (
    ProjectCreate,
    ProjectDeleteResult,
    ProjectOut,
    ProjectUpdate,
)

router = APIRouter(prefix="/api", tags=["projects"])


def _to_out(row: dict, req_count: int = 0) -> ProjectOut:
    return ProjectOut(
        project_id=row["project_id"],
        project_name=row["project_name"],
        description=row["description"],
        req_count=req_count,
    )


def _clean_name(project_name: str | None, alias: str | None) -> str:
    """project_name 与 name 二选一；空白名称直接 422。"""
    name = (project_name or alias or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="项目名称不能为空")
    return name


def _clean_description(description: str | None) -> str | None:
    text = (description or "").strip()
    return text or None


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


@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建项目",
)
def create_project(body: ProjectCreate) -> ProjectOut:
    name = _clean_name(body.project_name, body.name)
    row = repository.insert_project(
        project_name=name,
        description=_clean_description(body.description),
    )
    return _to_out(row, req_count=0)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectOut,
    summary="重命名 / 修改项目描述",
)
def update_project(project_id: int, body: ProjectUpdate) -> ProjectOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    fields: dict = {}
    if body.project_name is not None or body.name is not None:
        fields["project_name"] = _clean_name(body.project_name, body.name)
    if "description" in body.model_fields_set:
        fields["description"] = _clean_description(body.description)

    row = repository.update_project(project_id, fields)
    if row is None:  # 与上面的存在性检查之间的竞态兜底
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    counts = repository.project_counts(project_id)
    return _to_out(row, req_count=counts["requirements"])


@router.delete(
    "/projects/{project_id}",
    response_model=ProjectDeleteResult,
    summary="删除项目（有需求/文档时需 force=true 级联清理）",
)
def delete_project(
    project_id: int,
    force: Annotated[bool, Query(description="true=连同需求、文档、用例、执行记录一起删除")] = False,
) -> ProjectDeleteResult:
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    counts = repository.project_counts(project_id)
    if not force and (counts["requirements"] or counts["documents"]):
        raise HTTPException(
            status_code=409,
            detail=(
                f"项目还有 {counts['requirements']} 条需求、{counts['documents']} 份文档；"
                "确认要连同子数据一起删除请传 force=true"
            ),
        )

    removed = repository.delete_project(project_id)
    return ProjectDeleteResult(
        deleted=True,
        project_id=project_id,
        project_name=project["project_name"],
        requirements=removed["requirements"],
        documents=removed["documents"],
        cases=removed["cases"],
        executions=removed["executions"],
    )
