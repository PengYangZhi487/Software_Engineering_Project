"""Excel 导入导出：让 Excel 当编辑器，软件当追溯层。

- parse_requirements_xlsx / parse_cases_xlsx：解析上传的 .xlsx（表头容忍中英别名）
- build_requirements_workbook / build_cases_workbook：生成可编辑、可再导入的清单
- extract_json_requirements：把粘贴的大模型输出（JSON / ```json 包裹）转成行

解析函数只做纯转换，不碰数据库；写库在 routers/importer.py。
"""
from __future__ import annotations

import json
import re
from io import BytesIO
from typing import Any

from openpyxl import load_workbook

from App.services.xlsx_export import _add_table

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

REQ_HEADERS = ["需求编号", "标题", "描述", "类型", "优先级", "状态", "验收条件"]
CASE_HEADERS = [
    "用例编号", "关联需求", "用例标题", "前置条件", "操作步骤", "预期结果", "类型", "状态",
]

_REQ_COLUMNS = {
    "req_id": ["需求编号", "编号", "req_id", "ID", "id"],
    "title": ["标题", "需求标题", "title", "需求名称", "名称"],
    "description": ["描述", "需求描述", "description", "需求内容"],
    "req_type": ["类型", "需求类型", "req_type", "type"],
    "priority": ["优先级", "priority"],
    "status": ["状态", "status"],
    "acceptance": ["验收条件", "acceptance", "acceptance_criteria", "验收"],
}

_CASE_COLUMNS = {
    "tc_id": ["用例编号", "tc_id", "编号", "ID"],
    "req_id": ["关联需求", "需求编号", "req_id", "需求"],
    "title": ["用例标题", "标题", "title", "用例名称"],
    "preconditions": ["前置条件", "preconditions", "前提"],
    "steps": ["操作步骤", "测试步骤", "steps", "步骤"],
    "expected_result": ["预期结果", "expected_result", "预期"],
    "test_type": ["类型", "test_type", "用例类型"],
    "status": ["状态", "status"],
}

_CASE_STATUS = {"已生成", "已审核", "已驳回", "已执行"}
_REQ_STATUS = {"未审核", "已确认", "已驳回"}
_PRIORITIES = {"高", "中", "低"}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _split_list(text: str) -> list[str]:
    """验收条件 / 步骤：按换行或中英文分号拆分。"""
    parts: list[str] = []
    for line in (text or "").replace("\r", "\n").split("\n"):
        for piece in line.replace("；", ";").replace("、", ";").split(";"):
            item = piece.strip()
            if item:
                parts.append(item)
    return parts


def _map_req_type(value: str) -> str:
    v = value.lower().replace("-", "_").replace(" ", "_")
    if v in {"non_functional", "nonfunctional", "非功能", "非功能需求"}:
        return "non_functional"
    return "functional"


def _map_req_status(value: str) -> str:
    return value if value in _REQ_STATUS else "未审核"


def _map_priority(value: str) -> str:
    return value if value in _PRIORITIES else "中"


def _map_case_type(value: str) -> str:
    v = value.lower().strip()
    mapping = {
        "正常": "normal",
        "normal": "normal",
        "异常": "abnormal",
        "abnormal": "abnormal",
        "边界": "boundary",
        "boundary": "boundary",
    }
    return mapping.get(v, "normal")


def _map_case_status(value: str) -> str:
    return value if value in _CASE_STATUS else "已生成"


def _read_rows(content: bytes) -> tuple[list[str], list[list[Any]]]:
    wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        if not wb.sheetnames:
            return [], []
        ws = wb[wb.sheetnames[0]]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()
    if not rows:
        return [], []
    headers = [_norm(h) for h in rows[0]]
    return headers, [list(r) for r in rows[1:]]


def _pick(headers: list[str], row: list[Any], columns: dict[str, list[str]], key: str) -> str:
    for name in columns[key]:
        if name in headers:
            idx = headers.index(name)
            if idx < len(row):
                return _norm(row[idx])
    return ""


def _row_is_empty(row: list[Any]) -> bool:
    return not any(_norm(cell) for cell in row)


def parse_requirements_xlsx(content: bytes) -> list[dict]:
    headers, rows = _read_rows(content)
    parsed: list[dict] = []
    for offset, row in enumerate(rows, start=2):
        if _row_is_empty(row):
            continue
        parsed.append(
            {
                "row": offset,
                "req_id": _pick(headers, row, _REQ_COLUMNS, "req_id"),
                "title": _pick(headers, row, _REQ_COLUMNS, "title"),
                "description": _pick(headers, row, _REQ_COLUMNS, "description"),
                "req_type": _map_req_type(_pick(headers, row, _REQ_COLUMNS, "req_type")),
                "priority": _map_priority(_pick(headers, row, _REQ_COLUMNS, "priority")),
                "status": _map_req_status(_pick(headers, row, _REQ_COLUMNS, "status")),
                "acceptance": _split_list(_pick(headers, row, _REQ_COLUMNS, "acceptance")),
            }
        )
    return parsed


def parse_cases_xlsx(content: bytes) -> list[dict]:
    headers, rows = _read_rows(content)
    parsed: list[dict] = []
    for offset, row in enumerate(rows, start=2):
        if _row_is_empty(row):
            continue
        tc_raw = _pick(headers, row, _CASE_COLUMNS, "tc_id")
        match = re.search(r"(\d+)", tc_raw)
        parsed.append(
            {
                "row": offset,
                "tc_id": int(match.group(1)) if match else None,
                "req_id": _pick(headers, row, _CASE_COLUMNS, "req_id"),
                "title": _pick(headers, row, _CASE_COLUMNS, "title"),
                "preconditions": _split_list(_pick(headers, row, _CASE_COLUMNS, "preconditions")),
                "steps": _split_list(_pick(headers, row, _CASE_COLUMNS, "steps")),
                "expected_result": _pick(headers, row, _CASE_COLUMNS, "expected_result"),
                "test_type": _map_case_type(_pick(headers, row, _CASE_COLUMNS, "test_type")),
                "status": _map_case_status(_pick(headers, row, _CASE_COLUMNS, "status")),
            }
        )
    return parsed


def extract_json_requirements(text: str) -> list[dict]:
    """把粘贴的大模型输出转成行；编号不采信（由调用方程序生成）。"""
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    start = min((i for i in (raw.find("{"), raw.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError("没有找到 JSON 内容")
    end = max(raw.rfind("}"), raw.rfind("]"))
    if end <= start:
        raise ValueError("JSON 不完整")
    data = json.loads(raw[start : end + 1])

    items = data.get("requirements") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("JSON 里没有 requirements 数组")

    rows: list[dict] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        acceptance = item.get("acceptance_criteria") or item.get("acceptance") or []
        if isinstance(acceptance, str):
            acceptance = _split_list(acceptance)
        rows.append(
            {
                "row": idx,
                "req_id": "",  # 编号一律由程序生成
                "title": _norm(item.get("title") or item.get("name")),
                "description": _norm(item.get("description") or item.get("desc")),
                "req_type": _map_req_type(_norm(item.get("req_type") or item.get("type"))),
                "priority": _map_priority(_norm(item.get("priority"))),
                "status": "未审核",
                "acceptance": [str(x).strip() for x in acceptance if str(x).strip()],
            }
        )
    return rows


def build_requirements_workbook(requirements: list[dict]) -> bytes:
    rows = []
    for req in requirements:
        rows.append(
            [
                req.get("req_id", ""),
                req.get("title", ""),
                req.get("description", ""),
                "非功能" if req.get("req_type") == "non_functional" else "功能",
                req.get("priority") or "中",
                req.get("status", ""),
                "；".join(req.get("acceptance") or []),
            ]
        )
    wb = _new_workbook()
    _add_table(wb, "需求清单", REQ_HEADERS, rows, [12, 26, 52, 8, 8, 9, 46])
    return _save(wb)


def build_cases_workbook(cases: list[dict]) -> bytes:
    rows = []
    for case in cases:
        rows.append(
            [
                f"TC-{int(case['tc_id']):03d}",
                case.get("req_id") or "",
                case.get("title", ""),
                "；".join(case.get("preconditions") or []),
                "；".join(case.get("steps") or []),
                case.get("expected_result", ""),
                {"normal": "正常", "abnormal": "异常", "boundary": "边界"}.get(
                    case.get("test_type"), case.get("test_type", "")
                ),
                case.get("status", ""),
            ]
        )
    wb = _new_workbook()
    _add_table(wb, "用例清单", CASE_HEADERS, rows, [12, 12, 30, 26, 36, 32, 8, 9])
    return _save(wb)


def _new_workbook():
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)  # 不保留默认空 Sheet，否则导入会读到空表
    return wb


def _save(wb) -> bytes:
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
