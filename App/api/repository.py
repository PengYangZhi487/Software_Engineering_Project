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


def _requirement_of(row: Any) -> dict:
    data = dict(row)
    for key in ("acceptance", "source_location"):
        if data.get(key):
            try:
                data[key] = json.loads(data[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return data


def insert_requirement(
    *,
    req_id: str,
    project_id: int,
    title: str,
    description: str,
    acceptance: list[str],
    req_type: str,
    priority: str,
    is_ambiguous: int,
) -> dict:
    """手动创建的需求：没有来源文档，source_location 为空。"""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO Requirement
                (req_id, project_id, doc_id, title, description, acceptance,
                 req_type, priority, status, source_location, is_ambiguous)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, '未审核', NULL, ?)
            """,
            (
                req_id,
                project_id,
                title,
                description,
                json.dumps(acceptance, ensure_ascii=False),
                req_type,
                priority,
                is_ambiguous,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM Requirement WHERE project_id = ? AND req_id = ?",
            (project_id, req_id),
        ).fetchone()
        return _requirement_of(row)
    finally:
        conn.close()


def get_requirement(project_id: int, req_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM Requirement WHERE project_id = ? AND req_id = ?",
            (project_id, req_id),
        ).fetchone()
        if row is None:
            return None
        return _requirement_of(row)
    finally:
        conn.close()


# ---------- P5：测试用例 ----------

def _case_of(row: Any) -> dict:
    data = dict(row)
    for key in ("preconditions", "steps"):
        raw = data.get(key)
        if raw:
            try:
                parsed = json.loads(raw)
                data[key] = parsed if isinstance(parsed, list) else [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                data[key] = [str(raw)]
        else:
            data[key] = []
    return data


def list_cases(project_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT tc.* FROM TestCase tc
            JOIN Requirement r ON r.project_id = tc.project_id AND r.req_id = tc.req_id
            WHERE r.project_id = ?
            ORDER BY tc.tc_id
            """,
            (project_id,),
        ).fetchall()
        return [_case_of(r) for r in rows]
    finally:
        conn.close()


def get_case(tc_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM TestCase WHERE tc_id = ?", (tc_id,)).fetchone()
        return _case_of(row) if row else None
    finally:
        conn.close()


def insert_case(
    *,
    project_id: int,
    req_id: str,
    title: str,
    preconditions: list[str],
    steps: list[str],
    expected_result: str,
    test_type: str,
    status: str = "已生成",
) -> dict:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO TestCase
                (project_id, req_id, title, preconditions, steps, expected_result, test_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                req_id,
                title,
                json.dumps(preconditions, ensure_ascii=False),
                json.dumps(steps, ensure_ascii=False),
                expected_result,
                test_type,
                status,
            ),
        )
        tc_id = int(cur.lastrowid)
        conn.execute(
            "INSERT OR IGNORE INTO RequirementTestLink "
            "(project_id, req_id, tc_id, link_source) VALUES (?, ?, ?, ?)",
            (project_id, req_id, tc_id, "AI"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM TestCase WHERE tc_id = ?", (tc_id,)).fetchone()
        return _case_of(row)
    finally:
        conn.close()


def delete_cases_for_requirements(project_id: int, req_ids: list[str]) -> int:
    if not req_ids:
        return 0
    placeholders = ",".join("?" for _ in req_ids)
    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT tc_id FROM TestCase WHERE project_id = ? AND req_id IN ({placeholders})",
            (project_id, *req_ids),
        ).fetchall()
        tc_ids = [int(r["tc_id"]) for r in rows]
        if tc_ids:
            ph = ",".join("?" for _ in tc_ids)
            # 先删执行记录（外键引用 TestCase），再删关联与用例本身
            conn.execute(
                f"DELETE FROM Execution WHERE project_id = ? AND tc_id IN ({ph})",
                (project_id, *tc_ids),
            )
            conn.execute(
                f"DELETE FROM RequirementTestLink WHERE project_id = ? AND tc_id IN ({ph})",
                (project_id, *tc_ids),
            )
            conn.execute(f"DELETE FROM TestCase WHERE tc_id IN ({ph})", tc_ids)
            conn.commit()
        return len(tc_ids)
    finally:
        conn.close()


def update_case_status(tc_id: int, status: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE TestCase SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE tc_id = ?",
            (status, tc_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_case_fields(tc_id: int, fields: dict) -> bool:
    """按白名单字段更新用例；空字典直接返回 False。"""
    if not fields:
        return False
    sets = ", ".join(f"{key} = ?" for key in fields)
    conn = get_connection()
    try:
        cur = conn.execute(
            f"UPDATE TestCase SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE tc_id = ?",
            [*fields.values(), tc_id],
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------- 执行记录 ----------

def _execution_of(row: Any) -> dict:
    return dict(row)


def insert_execution(
    *,
    project_id: int,
    tc_id: int,
    result: str,
    actual_result: str | None = None,
    comments: str | None = None,
    tester: str | None = None,
    signature: str | None = None,
    environment: str | None = None,
) -> dict:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO Execution
                (project_id, tc_id, result, actual_result, comments, tester, signature, environment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, tc_id, result, actual_result, comments, tester, signature, environment),
        )
        exec_id = int(cur.lastrowid)
        conn.commit()
        row = conn.execute("SELECT * FROM Execution WHERE exec_id = ?", (exec_id,)).fetchone()
        return _execution_of(row)
    finally:
        conn.close()


def list_executions(project_id: int, tc_id: int | None = None) -> list[dict]:
    conn = get_connection()
    try:
        sql = "SELECT * FROM Execution WHERE project_id = ?"
        params: list = [project_id]
        if tc_id is not None:
            sql += " AND tc_id = ?"
            params.append(tc_id)
        sql += " ORDER BY exec_id"
        return [_execution_of(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def batch_update_case_status(project_id: int, tc_ids: list[int], status: str) -> int:
    if not tc_ids:
        return 0
    placeholders = ",".join("?" for _ in tc_ids)
    conn = get_connection()
    try:
        cur = conn.execute(
            f"UPDATE TestCase SET status = ?, updated_at = CURRENT_TIMESTAMP "
            f"WHERE project_id = ? AND tc_id IN ({placeholders})",
            [status, project_id, *tc_ids],
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ---------- P6：追踪矩阵 ----------

def trace_requirements(project_id: int) -> list[dict]:
    """项目需求 + 每条需求关联的用例编号与其中已审核的条数。"""
    conn = get_connection()
    try:
        reqs = [
            dict(r)
            for r in conn.execute(
                "SELECT req_id, title, status FROM Requirement WHERE project_id = ? ORDER BY req_id",
                (project_id,),
            ).fetchall()
        ]
        links = conn.execute(
            """
            SELECT l.req_id, tc.tc_id, tc.status
            FROM RequirementTestLink l
            JOIN TestCase tc ON tc.tc_id = l.tc_id
            WHERE l.project_id = ?
            """,
            (project_id,),
        ).fetchall()
    finally:
        conn.close()

    by_req: dict[str, list[dict]] = {}
    for row in links:
        by_req.setdefault(row["req_id"], []).append(
            {"tc_id": int(row["tc_id"]), "status": row["status"]}
        )

    for req in reqs:
        linked = by_req.get(req["req_id"], [])
        req["case_ids"] = [item["tc_id"] for item in linked]
        req["reviewed"] = sum(1 for item in linked if item["status"] == "已审核")
    return reqs


def trace_cases(project_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT tc.tc_id, tc.title, tc.test_type, tc.status, l.req_id
            FROM TestCase tc
            JOIN RequirementTestLink l ON l.tc_id = tc.tc_id
            WHERE l.project_id = ?
            ORDER BY tc.tc_id
            """,
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_quality_decisions(project_id: int) -> dict[str, str]:
    """fingerprint -> decision（confirmed / ignored）。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT fingerprint, decision FROM QualityDecision WHERE project_id = ?",
            (project_id,),
        ).fetchall()
        return {row["fingerprint"]: row["decision"] for row in rows}
    finally:
        conn.close()


def set_quality_decision(
    project_id: int, fingerprint: str, decision: str, note: str | None = None
) -> None:
    """写入或撤销裁决；decision=open 表示撤销。"""
    conn = get_connection()
    try:
        if decision == "open":
            conn.execute(
                "DELETE FROM QualityDecision WHERE project_id = ? AND fingerprint = ?",
                (project_id, fingerprint),
            )
        else:
            conn.execute(
                """
                INSERT INTO QualityDecision (project_id, fingerprint, decision, note)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, fingerprint) DO UPDATE SET
                    decision = excluded.decision,
                    note = excluded.note,
                    decided_at = CURRENT_TIMESTAMP
                """,
                (project_id, fingerprint, decision, note),
            )
        conn.commit()
    finally:
        conn.close()


def coverage_query(project_id: int) -> tuple[int, int]:
    """纯 SQL 计算覆盖率分子分母，用于和页面数字交叉验证（G4）。"""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM Requirement
                WHERE project_id = ? AND status = '已确认') AS confirmed,
              (SELECT COUNT(DISTINCT r.req_id)
                 FROM Requirement r
                 JOIN RequirementTestLink l
                   ON l.project_id = r.project_id AND l.req_id = r.req_id
                 JOIN TestCase tc ON tc.tc_id = l.tc_id
                WHERE r.project_id = ? AND r.status = '已确认' AND tc.status = '已审核') AS covered
            """,
            (project_id, project_id),
        ).fetchone()
        return int(row["confirmed"]), int(row["covered"])
    finally:
        conn.close()
