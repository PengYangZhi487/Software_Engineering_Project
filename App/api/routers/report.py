"""P8：质量报告与导出。

GET /api/projects/{project_id}/report        报告汇总（页面用）
GET /api/projects/{project_id}/report/export 导出 CSV（含 BOM，Excel 直接打开）

一致性：页面与 CSV 都来自同一份 _build()，覆盖率直接复用追踪模块的口径，
导出文件里的数字必须和页面完全一致。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response

from App.api import repository
from App.api.routers.trace import get_trace
from App.api.schemas import DocumentMeta, ReportCounts, ReportOut, ReportProject
from App.services import req_service
from App.services.quality_scan import scan_requirements

router = APIRouter(prefix="/api", tags=["report"])

CSV_BOM = "\ufeff"


def _build(project_id: int):
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    requirements = req_service.get_requirements(project_id)
    issues = scan_requirements(requirements)
    cases = repository.list_cases(project_id)
    documents = repository.list_documents(project_id)
    trace = get_trace(project_id)

    by_kind: dict[str, int] = {}
    for issue in issues:
        by_kind[issue["kind"]] = by_kind.get(issue["kind"], 0) + 1

    by_status: dict[str, int] = {}
    for case in cases:
        by_status[case["status"]] = by_status.get(case["status"], 0) + 1

    counts = ReportCounts(
        requirements=len(requirements),
        confirmed=sum(1 for r in requirements if r.get("status") == "已确认"),
        rejected=sum(1 for r in requirements if r.get("status") == "已驳回"),
        pending=sum(1 for r in requirements if r.get("status") == "未审核"),
        issues=len(issues),
        ambiguous=by_kind.get("ambiguous", 0),
        conflict=by_kind.get("conflict", 0),
        missing_acceptance=by_kind.get("missing_acceptance", 0),
        cases=len(cases),
        case_generated=by_status.get("已生成", 0),
        case_reviewed=by_status.get("已审核", 0),
        case_rejected=by_status.get("已驳回", 0),
        covered_requirements=trace.summary.covered,
        uncovered=trace.summary.uncovered,
        coverage_pct=trace.summary.coverage_pct,
    )

    return {
        "project": project,
        "documents": documents,
        "requirements": requirements,
        "issues": issues,
        "cases": cases,
        "counts": counts,
    }


@router.get(
    "/projects/{project_id}/report",
    response_model=ReportOut,
    summary="项目质量报告",
)
def get_report(project_id: int) -> ReportOut:
    data = _build(project_id)
    counts = data["counts"]
    project = data["project"]

    return ReportOut(
        project=ReportProject(
            project_id=project["project_id"],
            project_name=project["project_name"],
            description=project.get("description"),
        ),
        documents=[DocumentMeta(**d.model_dump()) for d in data["documents"]],
        counts=counts,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def _csv_rows(data: dict) -> list[list[str]]:
    counts = data["counts"]
    project = data["project"]
    rows: list[list[str]] = []

    rows.append(["# RATGP 质量报告"])
    rows.append(["# 项目", str(project["project_name"])])
    rows.append(["# 导出时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    rows.append(["# 需求总数", counts.requirements])
    rows.append(["# 已确认", counts.confirmed])
    rows.append(["# 已驳回", counts.rejected])
    rows.append(["# 未审核", counts.pending])
    rows.append(["# 质量问题", counts.issues])
    rows.append(["# 覆盖率(%)", counts.coverage_pct])
    rows.append(["# 覆盖口径", "至少关联一条已审核用例的已确认需求 / 已确认需求总数"])
    rows.append([])

    rows.append(["# 需求清单"])
    rows.append(["req_id", "title", "type", "status", "ambiguous", "source_para", "case_count", "covered"])
    case_count: dict[str, int] = {}
    for case in data["cases"]:
        rid = case.get("req_id") or ""
        case_count[rid] = case_count.get(rid, 0) + 1
    for req in data["requirements"]:
        location = req.get("source_location") or {}
        rows.append(
            [
                req["req_id"],
                req["title"],
                req.get("req_type", ""),
                req.get("status", ""),
                "是" if req.get("is_ambiguous") else "否",
                location.get("para_no", ""),
                case_count.get(req["req_id"], 0),
                "是" if case_count.get(req["req_id"], 0) else "否",
            ]
        )
    rows.append([])

    rows.append(["# 质量问题"])
    rows.append(["issue_id", "kind", "title", "req_ids", "detail"])
    for issue in data["issues"]:
        rows.append(
            [
                issue["issue_id"],
                issue["kind"],
                issue["title"],
                " / ".join(issue["req_ids"]),
                issue["detail"],
            ]
        )
    rows.append([])

    rows.append(["# 测试用例"])
    rows.append(["tc_id", "req_id", "title", "test_type", "status", "expected_result"])
    for case in data["cases"]:
        rows.append(
            [
                case["tc_id"],
                case.get("req_id") or "",
                case["title"],
                case["test_type"],
                case["status"],
                case["expected_result"],
            ]
        )
    return rows


@router.get(
    "/projects/{project_id}/report/export",
    summary="导出质量报告 CSV",
)
def export_report(
    project_id: int,
    fmt: str = Query("csv", alias="format", description="目前只支持 csv"),
) -> Response:
    if fmt.lower() != "csv":
        raise HTTPException(status_code=400, detail="目前只支持 CSV 导出")

    data = _build(project_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerows(_csv_rows(data))

    content = CSV_BOM + buffer.getvalue()
    filename = f"ratgp-report-project{project_id}.csv"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
