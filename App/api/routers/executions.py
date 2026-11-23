"""执行记录：把「生成 ≠ 执行 ≠ 通过」的最后一环补上。

GET  /api/projects/{project_id}/executions        项目执行记录（可按用例过滤）
POST /api/projects/{project_id}/executions        登记一次执行（结果 / 实际结果 / comments / 执行人 / 签名）
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from App.api import repository
from App.api.schemas import ExecutionCreate, ExecutionListOut, ExecutionOut

router = APIRouter(prefix="/api", tags=["executions"])

RESULTS = ("pass", "fail", "blocked")


def _to_out(row: dict) -> ExecutionOut:
    return ExecutionOut(
        exec_id=int(row["exec_id"]),
        project_id=int(row["project_id"]),
        tc_id=int(row["tc_id"]),
        result=row.get("result") or "",
        actual_result=row.get("actual_result"),
        comments=row.get("comments"),
        tester=row.get("tester"),
        signature=row.get("signature"),
        environment=row.get("environment"),
        executed_at=row.get("executed_at"),
    )


@router.get(
    "/projects/{project_id}/executions",
    response_model=ExecutionListOut,
    summary="项目执行记录",
)
def list_executions(
    project_id: int,
    tc_id: int | None = None,
) -> ExecutionListOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    rows = repository.list_executions(project_id, tc_id)
    return ExecutionListOut(items=[_to_out(r) for r in rows], total=len(rows))


@router.post(
    "/projects/{project_id}/executions",
    response_model=ExecutionOut,
    status_code=201,
    summary="登记一次测试执行",
)
def create_execution(project_id: int, body: ExecutionCreate) -> ExecutionOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    case = repository.get_case(body.tc_id)
    if case is None or int(case.get("project_id") or 0) != project_id:
        raise HTTPException(status_code=404, detail=f"用例 {body.tc_id} 不存在")

    if body.result not in RESULTS:
        raise HTTPException(
            status_code=422,
            detail=f"执行结果只支持 {list(RESULTS)}",
        )

    row = repository.insert_execution(
        project_id=project_id,
        tc_id=body.tc_id,
        result=body.result,
        actual_result=(body.actual_result or "").strip() or None,
        comments=(body.comments or "").strip() or None,
        tester=(body.tester or "").strip() or None,
        signature=(body.signature or "").strip() or None,
        environment=(body.environment or "").strip() or None,
    )
    return _to_out(row)
