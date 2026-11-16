"""P6：需求 × 用例追踪矩阵与覆盖率。

GET /api/projects/{project_id}/trace            矩阵 + 汇总
GET /api/projects/{project_id}/trace/coverage   只用 SQL 复算覆盖率，并和矩阵口径交叉校验

覆盖率口径（写死在这里，报告页与矩阵页都引用同一份）：
    分子 = 至少关联一条「已审核」用例的已确认需求数
    分母 = 已确认需求总数
「已生成但未审核」的用例不计入分子，避免把机器生成的候选算成覆盖。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from App.api import repository
from App.api.schemas import CoverageOut, TraceCase, TraceOut, TraceRequirement, TraceSummary

router = APIRouter(prefix="/api", tags=["trace"])


def _pct(covered: int, total: int) -> int:
    return round(covered / total * 100) if total else 0


@router.get(
    "/projects/{project_id}/trace",
    response_model=TraceOut,
    summary="需求 × 用例追踪矩阵",
)
def get_trace(project_id: int) -> TraceOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    req_rows = repository.trace_requirements(project_id)
    case_rows = repository.trace_cases(project_id)

    confirmed = [r for r in req_rows if r["status"] == "已确认"]
    covered_ids = {r["req_id"] for r in confirmed if r["reviewed"] > 0}
    linked_any = sum(1 for r in confirmed if r["case_ids"])

    summary = TraceSummary(
        confirmed=len(confirmed),
        covered=len(covered_ids),
        coverage_pct=_pct(len(covered_ids), len(confirmed)),
        linked_any=linked_any,
        cases=len(case_rows),
        reviewed_cases=sum(1 for c in case_rows if c["status"] == "已审核"),
        uncovered=len(confirmed) - linked_any,
    )

    return TraceOut(
        summary=summary,
        requirements=[
            TraceRequirement(
                req_id=r["req_id"],
                title=r["title"],
                status=r["status"],
                case_ids=r["case_ids"],
                reviewed=r["reviewed"],
                covered=r["req_id"] in covered_ids,
            )
            for r in req_rows
        ],
        cases=[
            TraceCase(
                tc_id=int(c["tc_id"]),
                title=c["title"],
                test_type=c["test_type"],
                status=c["status"],
                req_id=c["req_id"],
            )
            for c in case_rows
        ],
    )


@router.get(
    "/projects/{project_id}/trace/coverage",
    response_model=CoverageOut,
    summary="覆盖率（纯 SQL 复算）",
)
def get_coverage(project_id: int) -> CoverageOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    confirmed, sql_covered = repository.coverage_query(project_id)

    # 用矩阵口径再算一遍，确认两边一致（G4：页面数字可独立复算）
    req_rows = repository.trace_requirements(project_id)
    matrix_confirmed = [r for r in req_rows if r["status"] == "已确认"]
    matrix_covered = sum(1 for r in matrix_confirmed if r["reviewed"] > 0)

    return CoverageOut(
        confirmed=confirmed,
        covered=matrix_covered,
        coverage_pct=_pct(matrix_covered, confirmed),
        sql_covered=sql_covered,
        consistent=(confirmed == len(matrix_confirmed) and sql_covered == matrix_covered),
    )
