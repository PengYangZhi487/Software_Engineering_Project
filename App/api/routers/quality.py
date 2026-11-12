"""P4：需求质量扫描。

GET /api/projects/{project_id}/quality/issues

扫描是确定性的（同一份数据每次结果一致），不改数据、不调 LLM，
因此可以直接 GET，不需要先 POST scan。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from App.api import repository
from App.api.schemas import QualityIssue, QualitySummary
from App.services import req_service
from App.services.quality_scan import scan_requirements

router = APIRouter(prefix="/api", tags=["quality"])


@router.get(
    "/projects/{project_id}/quality/issues",
    response_model=QualitySummary,
    summary="需求质量问题扫描",
)
def list_issues(project_id: int) -> QualitySummary:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    rows = req_service.get_requirements(project_id)
    issues = scan_requirements(rows)

    by_kind: dict[str, int] = {}
    for issue in issues:
        by_kind[issue["kind"]] = by_kind.get(issue["kind"], 0) + 1

    return QualitySummary(
        items=[QualityIssue(**issue) for issue in issues],
        total=len(issues),
        by_kind=by_kind,
    )
