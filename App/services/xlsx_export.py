"""Excel 导出：需求清单 / 测试用例执行表 / 覆盖矩阵。

数据来源与页面、CSV 完全同源（report._build + trace 口径），
所以导出的数字和页面一致；执行表额外合并 Execution 表。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HEADER_FILL = PatternFill("solid", fgColor="2F3A4A")
_HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
_TITLE_FONT = Font(bold=True, size=14)
_THIN = Side(style="thin", color="D9DEE7")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_WRAP = Alignment(vertical="top", wrap_text=True)

_RESULT_LABEL = {"pass": "通过", "fail": "失败", "blocked": "阻塞"}
_TYPE_LABEL = {"normal": "正常", "abnormal": "异常", "boundary": "边界"}
# SQLite CURRENT_TIMESTAMP 是 UTC；导出给人看，统一转东八区
_UTC_TO_CST = timedelta(hours=8)


def _format_time(value: str | None) -> str:
    if not value:
        return ""
    try:
        return (datetime.strptime(value, "%Y-%m-%d %H:%M:%S") + _UTC_TO_CST).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except ValueError:
        return value


def _join_list(value) -> str:
    if isinstance(value, list):
        return "；".join(str(v) for v in value if str(v).strip())
    return str(value or "")


def _add_table(
    wb: Workbook,
    title: str,
    headers: list[str],
    rows: list[list],
    widths: list[int],
) -> None:
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        cell.border = _BORDER
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP
            cell.border = _BORDER
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def build_report_workbook(data: dict, executions: list[dict]) -> bytes:
    """把 report._build() 的数据与执行记录拼成 xlsx。"""
    project = data["project"]
    counts = data["counts"]
    requirements = data["requirements"]
    cases = data["cases"]
    issues = data["issues"]

    wb = Workbook()
    wb.remove(wb.active)

    # 1. 概览
    ws = wb.create_sheet("概览")
    ws["A1"] = f"RATGP 质量报告 · {project['project_name']}"
    ws["A1"].font = _TITLE_FONT
    overview = [
        ("导出时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("需求总数", counts.requirements),
        ("已确认", counts.confirmed),
        ("已驳回", counts.rejected),
        ("未审核", counts.pending),
        ("质量问题", counts.issues),
        ("用例总数", counts.cases),
        ("已生成用例", counts.case_generated),
        ("已审核用例", counts.case_reviewed),
        ("已驳回用例", counts.case_rejected),
        ("覆盖需求数", counts.covered_requirements),
        ("未覆盖需求", counts.uncovered),
        ("覆盖率(%)", counts.coverage_pct),
        ("覆盖口径", "至少关联一条已审核用例的已确认需求 / 已确认需求总数"),
        ("执行记录", f"{len(executions)} 条"),
    ]
    for offset, (key, value) in enumerate(overview, start=3):
        ws.cell(row=offset, column=1, value=key).font = Font(bold=True)
        ws.cell(row=offset, column=2, value=value).alignment = Alignment(wrap_text=True)
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 64

    # 2. 需求清单
    case_count: dict[str, int] = {}
    for case in cases:
        rid = case.get("req_id") or ""
        case_count[rid] = case_count.get(rid, 0) + 1

    req_rows = []
    for req in requirements:
        location = req.get("source_location") or {}
        req_rows.append(
            [
                req["req_id"],
                req["title"],
                req.get("description", ""),
                "非功能" if req.get("req_type") == "non_functional" else "功能",
                req.get("priority", ""),
                req.get("status", ""),
                _join_list(req.get("acceptance")),
                location.get("para_no", ""),
                case_count.get(req["req_id"], 0),
            ]
        )
    _add_table(
        wb,
        "需求清单",
        ["需求编号", "标题", "描述", "类型", "优先级", "状态", "验收条件", "来源段落", "关联用例数"],
        req_rows,
        [12, 26, 46, 8, 8, 9, 40, 10, 12],
    )

    # 3. 测试用例执行表：每次执行一行；没执行过的用例也保留一行
    exec_by_tc: dict[int, list[dict]] = {}
    for execution in executions:
        exec_by_tc.setdefault(int(execution["tc_id"]), []).append(execution)

    exec_rows = []
    for case in cases:
        tc_id = int(case["tc_id"])
        runs: list[dict | None] = list(exec_by_tc.get(tc_id) or [None])
        for execution in runs:
            run = execution or {}
            exec_rows.append(
                [
                    f"TC-{tc_id:03d}",
                    case.get("req_id") or "",
                    case["title"],
                    _join_list(case.get("preconditions")),
                    _join_list(case.get("steps")),
                    case.get("expected_result", ""),
                    _TYPE_LABEL.get(case.get("test_type"), case.get("test_type", "")),
                    case.get("status", ""),
                    _RESULT_LABEL.get(run.get("result"), ""),
                    run.get("actual_result") or "",
                    run.get("comments") or "",
                    run.get("tester") or "",
                    run.get("signature") or "",
                    run.get("environment") or "",
                    _format_time(run.get("executed_at")),
                ]
            )
    _add_table(
        wb,
        "测试用例执行表",
        [
            "用例编号", "关联需求", "用例标题", "前置条件", "操作步骤", "预期结果",
            "类型", "用例状态", "执行结果", "实际结果", "测试comments",
            "执行人", "测试者签名", "执行环境", "执行时间",
        ],
        exec_rows,
        [11, 11, 28, 24, 34, 30, 8, 9, 9, 28, 26, 10, 12, 16, 18],
    )

    # 4. 覆盖矩阵
    reviewed: dict[str, int] = {}
    linked: dict[str, int] = {}
    for case in cases:
        rid = case.get("req_id") or ""
        linked[rid] = linked.get(rid, 0) + 1
        if case.get("status") == "已审核":
            reviewed[rid] = reviewed.get(rid, 0) + 1

    matrix_rows = []
    for req in requirements:
        rid = req["req_id"]
        matrix_rows.append(
            [
                rid,
                req["title"],
                req.get("status", ""),
                linked.get(rid, 0),
                reviewed.get(rid, 0),
                "是" if reviewed.get(rid, 0) > 0 and req.get("status") == "已确认" else "否",
            ]
        )
    matrix_rows.append(["", "", "", "", "", ""])
    matrix_rows.append(
        [
            "已确认需求",
            counts.confirmed,
            "覆盖需求",
            counts.covered_requirements,
            "覆盖率(%)",
            counts.coverage_pct,
        ]
    )
    _add_table(
        wb,
        "覆盖矩阵",
        ["需求编号", "标题", "需求状态", "用例数", "已审核用例", "是否覆盖"],
        matrix_rows,
        [12, 30, 10, 9, 12, 10],
    )

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
