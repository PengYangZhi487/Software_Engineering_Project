# App/services/doc_service.py
import os
import logging
from docx import Document

logger = logging.getLogger(__name__)

ALLOWED_EXTS = {".txt", ".docx"}


def parse_docx(file_path: str):
    """解析 DOCX，返回 (全文, 段落索引列表)。

    段落索引额外带 style（Heading 1 / Heading 2 / Normal ...），
    供 API 层标记标题、前端做大纲；locate_service 只读 raw / para_no，不受影响。
    """
    doc = Document(file_path)
    full_text = []
    para_index = []
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            full_text.append(para.text)
            style = para.style.name if para.style is not None else "Normal"
            para_index.append({"para_no": i, "raw": para.text, "style": style})
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
        raise ValueError(f"无法识别文件编码: {file_path}")

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
        raise FileNotFoundError(file_path)

    if ext == ".docx":
        return parse_docx(file_path)
    return parse_txt(file_path)
