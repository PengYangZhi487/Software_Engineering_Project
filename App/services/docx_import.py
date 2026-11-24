"""Word（.docx）需求表导入：让 Word 里的需求表也能当编辑器。

约定与 Excel 导入完全一致：

- 表格第一行是表头，之后一行一条需求；
- 列名容忍中英别名（``需求编号 / 编号 / req_id / ID`` 都指同一列），
  表头里带「（必填）」「*」这类修饰也能认出来；
- 字段清洗复用 ``import_export``（类型 / 优先级 / 状态 / 验收条件）；
- 解析函数只做纯转换，不碰数据库；写库在 ``routers/importer.py``，
  与 xlsx 共用 ``_apply_requirements``。

文档里可以有多张表格、表格前后也有正文：只有「表头看起来像需求表」的表格
才会被解析，其余表格（修订记录、评审签字之类）直接跳过。
"""
from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from docx import Document

from App.services.import_export import (
    _REQ_COLUMNS,
    _map_priority,
    _map_req_status,
    _map_req_type,
    _norm,
    _split_list,
)

# 表头修饰：括号说明、空白、下划线、连字符、中英文冒号、星号
_PARENS = re.compile(r"[（(][^）)]*[）)]")
_SEPARATORS = re.compile(r"[\s_\-—:：*＊]+")


def _header_key(value: Any) -> str:
    """表头归一：``需求编号（必填）`` -> ``需求编号``，``Req-ID *`` -> ``reqid``。"""
    text = _PARENS.sub("", _norm(value))
    return _SEPARATORS.sub("", text).lower()


# (归一后的别名, 字段名)：直接取自 Excel 导入的列映射，保证两边认列一致
_ALIASES: list[tuple[str, str]] = [
    (key, field)
    for field, names in _REQ_COLUMNS.items()
    for key in (_header_key(name) for name in names)
    if key
]


def _match_field(header: Any) -> str | None:
    """把一个表头映射到需求字段；先精确匹配，再按最长的包含关系兜底。"""
    key = _header_key(header)
    if not key:
        return None
    for alias, field in _ALIASES:
        if key == alias:
            return field
    best: tuple[int, str] | None = None
    for alias, field in _ALIASES:
        # 别名太短（如 id）不做包含匹配，避免误认
        if len(alias) >= 2 and (alias in key or key in alias):
            if best is None or len(alias) > best[0]:
                best = (len(alias), field)
    return best[1] if best else None


def _column_map(headers: list[str]) -> dict[int, str]:
    """列号 -> 字段名；同一字段只认第一次出现的那列。"""
    mapping: dict[int, str] = {}
    used: set[str] = set()
    for idx, header in enumerate(headers):
        field = _match_field(header)
        if field and field not in used:
            mapping[idx] = field
            used.add(field)
    return mapping


def _grid(table) -> list[list[str]]:
    """表格 -> 规整的二维文本。

    纵向合并（vMerge）延续出来的格子与上一行是同一个 XML 节点，这里置空，
    否则编号会被重复读成“每行都更新同一条需求”。
    """
    rows: list[list[str]] = []
    prev_tcs: list[Any] = []
    for row in table.rows:
        cells = list(row.cells)
        tcs = [cell._tc for cell in cells]
        values = [_norm(cell.text) for cell in cells]
        if prev_tcs and len(prev_tcs) == len(tcs):
            for i, tc in enumerate(tcs):
                if prev_tcs[i] is tc:
                    values[i] = ""
        rows.append(values)
        prev_tcs = tcs
    return rows


def _first_line(value: str) -> str:
    """单值字段取第一行：合并单元格里可能并列两段（编号/标题不会跨行）。"""
    for line in (value or "").splitlines():
        text = line.strip()
        if text:
            return text
    return ""


def _row_dict(mapping: dict[int, str], values: list[str], row_no: int) -> dict:
    cells = {field: values[idx] for idx, field in mapping.items() if idx < len(values)}
    return {
        "row": row_no,
        "req_id": _first_line(cells.get("req_id", "")),
        "title": _first_line(cells.get("title", "")),
        "description": cells.get("description", "").strip(),
        "req_type": _map_req_type(_first_line(cells.get("req_type", ""))),
        "priority": _map_priority(_first_line(cells.get("priority", ""))),
        "status": _map_req_status(_first_line(cells.get("status", ""))),
        "acceptance": _split_list(cells.get("acceptance", "")),
    }


def parse_requirements_docx(content: bytes) -> list[dict]:
    """解析上传的 .docx 需求表，返回与 ``parse_requirements_xlsx`` 同构的行。"""
    if not content:
        raise ValueError("文件为空")
    try:
        doc = Document(BytesIO(content))
    except Exception as exc:  # 损坏的 / 其实是 zip 但不是 docx 的文件
        raise ValueError(f"不是有效的 .docx 文件：{exc}") from exc

    parsed: list[dict] = []
    row_no = 1  # 与 Excel 一致：表头是第 1 行，数据从第 2 行起（跨表连续编号）
    for table in doc.tables:
        grid = _grid(table)
        if len(grid) < 2:
            continue
        mapping = _column_map(grid[0])
        # 至少要认出两个需求列，且其中包含标题或描述，才当成需求表
        if len(mapping) < 2 or not ({"title", "description"} & set(mapping.values())):
            continue
        for values in grid[1:]:
            row_no += 1
            if not any(values):
                continue
            parsed.append(_row_dict(mapping, values, row_no))
    return parsed
