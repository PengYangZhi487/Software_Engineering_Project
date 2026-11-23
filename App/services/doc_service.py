# App/services/doc_service.py
import os
import logging

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)

ALLOWED_EXTS = {".txt", ".docx"}

# 识别“表头行”的关键词：命中 2 个以上、且每个单元格都不长，就当作列名
_HEADER_HINTS = (
    "编号", "序号", "需求", "名称", "标题", "描述", "说明",
    "验收", "模块", "优先级", "类型", "状态", "备注",
)

_MAX_TABLE_DEPTH = 3


def _iter_blocks(parent):
    """按文档真实顺序产出 Paragraph / Table；parent 可以是 Document 或单元格。"""
    if isinstance(parent, DocxDocument):
        element = parent.element.body
    else:
        element = getattr(parent, "_tc", None)
        if element is None:
            return
    for child in element.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _cell_text(cell, depth: int) -> str:
    """单元格文本：自身段落 + 嵌套表格（限制层数，避免异常文档递归）。"""
    parts = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
    if depth < _MAX_TABLE_DEPTH:
        for inner in cell.tables:
            inner_lines = _table_lines(inner, depth + 1)
            if inner_lines:
                parts.append("；".join(inner_lines))
    return " ".join(parts)


def _row_cells(row, depth: int) -> list[str]:
    """一行表格转成单元格文本列表；水平合并的格子只取一次。"""
    seen: set[int] = set()
    cells: list[str] = []
    for cell in row.cells:
        key = id(cell._tc)
        if key in seen:
            continue
        seen.add(key)
        text = _cell_text(cell, depth)
        if text:
            cells.append(text)
    return cells


def _looks_like_header(cells: list[str]) -> bool:
    if not cells or any(len(c) > 20 for c in cells):
        return False
    hits = sum(1 for c in cells if any(hint in c for hint in _HEADER_HINTS))
    return hits >= 2


def _table_lines(table: Table, depth: int = 0) -> list[str]:
    """表格转成若干行文本。

    第一行像表头时，把它当列名，数据行输出成
    ``编号：REQ-001 | 名称：课程容量 | 描述：……``；
    否则退化成 ``a | b | c``，不猜、不丢。
    """
    rows: list[list[str]] = []
    for row in table.rows:
        cells = _row_cells(row, depth)
        if cells:
            rows.append(cells)
    if not rows:
        return []

    if len(rows) > 1 and _looks_like_header(rows[0]):
        header, body = rows[0], rows[1:]
        lines: list[str] = []
        for cells in body:
            parts = []
            for i, value in enumerate(cells):
                name = header[i] if i < len(header) else f"列{i + 1}"
                parts.append(f"{name}：{value}")
            lines.append(" | ".join(parts))
        return lines

    return [" | ".join(cells) for cells in rows]


def parse_docx(file_path: str):
    """解析 DOCX，返回 (全文, 段落索引列表)。

    按文档真实顺序遍历段落和表格：
    - 段落保留 Word 样式（Heading 1 / Heading 2 / Normal ...）；
    - 表格一行转一段，style 标记为 ``Table``，有表头时带列名。

    ``para_no`` 是“非空块”的连续序号（段落与表格行共用一套），
    保证前端展示、来源定位和版本比对用的是同一套坐标。
    """
    doc = Document(file_path)
    full_text: list[str] = []
    para_index: list[dict] = []
    idx = 0

    for block in _iter_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            style = block.style.name if block.style is not None else "Normal"
            para_index.append({"para_no": idx, "raw": text, "style": style})
            full_text.append(text)
            idx += 1
        else:
            for line in _table_lines(block):
                para_index.append({"para_no": idx, "raw": line, "style": "Table"})
                full_text.append(line)
                idx += 1

    return "\n".join(full_text), para_index


def parse_txt(file_path: str):
    """解析 TXT（UTF-8 / GBK 兜底），返回 (全文, 行索引列表)。"""
    text = None
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("无法识别文件编码，请另存为 UTF-8 或 GBK")

    full_text = []
    para_index = []
    for i, line in enumerate(text.splitlines()):
        if line.strip():
            full_text.append(line)
            para_index.append({"para_no": i, "raw": line, "style": "Normal"})
    return "\n".join(full_text), para_index


def parse_document(file_path: str):
    """按扩展名分发。返回 (全文, 段落/行索引列表)。"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"不支持的文件类型: {ext}，仅支持 {ALLOWED_EXTS}")
    if not os.path.exists(file_path):
        raise FileNotFoundError("文档不存在")

    if ext == ".docx":
        return parse_docx(file_path)
    return parse_txt(file_path)
