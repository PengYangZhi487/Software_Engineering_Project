"""P4：需求质量扫描与裁决。

GET   /api/projects/{project_id}/quality/issues
PATCH /api/projects/{project_id}/quality/issues/{fingerprint}

扫描是确定性的；裁决存在 QualityDecision 表里，按内容指纹挂接。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from App.api import repository
from App.api.schemas import QualityDecisionUpdate, QualityIssue, QualitySummary
from App.services import req_service
from App.services.quality_scan import scan_requirements

router = APIRouter(prefix="/api", tags=["quality"])

_DECISIONS = {"open", "confirmed", "ignored"}


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
    decisions = repository.get_quality_decisions(project_id)

    by_kind: dict[str, int] = {}
    for issue in issues:
        issue["decision"] = decisions.get(issue["fingerprint"], "open")
        by_kind[issue["kind"]] = by_kind.get(issue["kind"], 0) + 1

    decided = sum(1 for issue in issues if issue["decision"] != "open")
    return QualitySummary(
        items=[QualityIssue(**issue) for issue in issues],
        total=len(issues),
        open=len(issues) - decided,
        decided=decided,
        by_kind=by_kind,
    )


@router.patch(
    "/projects/{project_id}/quality/issues/{fingerprint}",
    summary="裁决质量问题（确认 / 忽略 / 撤销）",
)
def decide_issue(
    project_id: int, fingerprint: str, body: QualityDecisionUpdate
) -> dict:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    if body.decision not in _DECISIONS:
        raise HTTPException(
            status_code=422,
            detail=f"非法裁决 {body.decision}，只支持 {sorted(_DECISIONS)}",
        )

    repository.set_quality_decision(project_id, fingerprint, body.decision, body.note)
    return {"fingerprint": fingerprint, "decision": body.decision}
