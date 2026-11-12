"""所有 SQL 都收在这里，router 只负责协议层。"""
from __future__ import annotations

import json
from typing import Any

from App.dao.db import get_connection
from App.api.schemas import DocumentMeta, Paragraph


def _paragraphs_of(row: Any) -> list[Paragraph]:
    raw = row["para_index"]
    items = json.loads(raw) if raw else []
    out: list[Paragraph] = []
    for p in items:
        style = p.get("style") or "Normal"
        out.append(
            Paragraph(
                para_no=int(p.get("para_no", 0)),
                text=p.get("raw") or "",
                style=style,
                is_heading=style.startswith("Heading"),
            )
        )
    return out


def _meta_of(row: Any) -> DocumentMeta:
    return DocumentMeta(
        doc_id=row["doc_id"],
        project_id=row["project_id"],
        filename=row["filename"],
        version=row["version"],
        upload_time=str(row["upload_time"]) if row["upload_time"] else None,
        paragraphs=len(_paragraphs_of(row)),
        chars=len(row["content_text"] or ""),
        file_path=row["file_path"],
    )


def list_projects() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT p.project_id, p.project_name, p.description,
                   (SELECT COUNT(*) FROM Requirement r WHERE r.project_id = p.project_id) AS req_count
            FROM Project p
            ORDER BY p.project_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project(project_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT project_id, project_name, description FROM Project WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def insert_document(
    *,
    project_id: int,
    filename: str,
    version: str,
    content_text: str,
    para_index: list[dict],
    file_path: str,
) -> DocumentMeta:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO Document (project_id, filename, version, content_text, para_index, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                filename,
                version,
                content_text,
                json.dumps(para_index, ensure_ascii=False),
                file_path,
            ),
        )
        conn.commit()
        doc_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM Document WHERE doc_id = ?", (doc_id,)).fetchone()
        return _meta_of(row)
    finally:
        conn.close()


def list_documents(project_id: int) -> list[DocumentMeta]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM Document WHERE project_id = ? ORDER BY doc_id DESC",
            (project_id,),
        ).fetchall()
        return [_meta_of(r) for r in rows]
    finally:
        conn.close()


def get_document(doc_id: int) -> DocumentMeta | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM Document WHERE doc_id = ?", (doc_id,)).fetchone()
        return _meta_of(row) if row else None
    finally:
        conn.close()


def get_paragraphs(doc_id: int) -> list[Paragraph] | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT para_index FROM Document WHERE doc_id = ?", (doc_id,)).fetchone()
        return _paragraphs_of(row) if row else None
    finally:
        conn.close()


# ---------- P3：需求 ----------

def get_document_source(doc_id: int) -> tuple[str, list[dict]] | None:
    """取文档正文与结构化段落索引，供抽取与段落定位使用。"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content_text, para_index FROM Document WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        if not row:
            return None
        para_index = json.loads(row["para_index"]) if row["para_index"] else []
        return row["content_text"] or "", para_index
    finally:
        conn.close()


def latest_document_id(project_id: int) -> int | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT doc_id FROM Document WHERE project_id = ? ORDER BY doc_id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        return int(row["doc_id"]) if row else None
    finally:
        conn.close()


def max_requirement_number(project_id: int) -> int:
    """项目里已有需求的最大编号（CR-012 → 12），用于续号。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT req_id FROM Requirement WHERE project_id = ?", (project_id,)
        ).fetchall()
    finally:
        conn.close()

    best = 0
    for r in rows:
        digits = "".join(ch for ch in (r["req_id"] or "") if ch.isdigit())
        if digits:
            best = max(best, int(digits))
    return best


def get_requirement(req_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM Requirement WHERE req_id = ?", (req_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
    finally:
        conn.close()

    for key in ("acceptance", "source_location"):
        if data.get(key):
            try:
                data[key] = json.loads(data[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return data
