# App/services/req_service.py
"""
需求入库服务：把 LLM 提取的 RequirementList 写入 ratgp.db。
只负责"落库与查询"，不做解析、不调 LLM。
"""
import json
import logging
from typing import List, Dict, Optional, Union

from ..dao.db import get_connection
from .llm_service import Requirement, RequirementList
from .quality_service import has_ambiguous
from .locate_service import locate_requirement

logger = logging.getLogger(__name__)


# ---------- 内部工具 ----------
def _to_acceptance_text(criteria: List[str]) -> str:
    """验收条件列表存 JSON 文本，保留结构，方便后面用例生成时逐条对比。"""
    return json.dumps(criteria or [], ensure_ascii=False)


def _normalize_req_type(v: Optional[str]) -> str:
    """双保险：即使 LLM 返回中划线/空格，入库前也归一化。"""
    raw = (v or "functional").strip().lower().replace("-", "_").replace(" ", "_")
    return raw if raw in {"functional", "non_functional"} else "functional"


# ---------- 清理 ----------
def clear_project_requirements(project_id: int) -> int:
    """清空指定项目的需求（用于测试重建）。返回删除条数。"""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM Requirement WHERE project_id = ?", (project_id,))
        conn.commit()
        logger.info("已清空 project_id=%s 的需求 %d 条", project_id, cur.rowcount)
        return cur.rowcount
    finally:
        conn.close()


# ---------- 写入 ----------
def save_requirements(
    project_id: int,
    doc_id: Optional[int],
    requirements: Union[RequirementList, List[Requirement], List[dict]],
    para_index: Optional[List[Dict]] = None,
    clear_first: bool = False,
) -> Dict[str, int]:
    """
    批量写入需求。

    :param project_id: 所属项目
    :param doc_id:     来源文档（可 None）
    :param requirements: RequirementList / List[Requirement] / List[dict]
    :param para_index:  doc_service.parse_docx 的段落索引；给了就补 source_location
    :param clear_first: True 则先清空该项目所有需求（测试重建时用）
    :return: {"saved": N, "skipped": M, "ambiguous": K}
    """
    # 统一成 list[dict]
    if isinstance(requirements, RequirementList):
        reqs = [r.model_dump() for r in requirements.requirements]
    elif requirements and hasattr(requirements[0], "model_dump"):
        reqs = [r.model_dump() for r in requirements]  # type: ignore
    else:
        reqs = list(requirements or [])

    if not reqs:
        logger.warning("requirements 为空，跳过写入")
        return {"saved": 0, "skipped": 0, "ambiguous": 0}

    conn = get_connection()
    saved = skipped = ambiguous = 0
    try:
        if clear_first:
            conn.execute("DELETE FROM Requirement WHERE project_id = ?", (project_id,))
            conn.commit()
            logger.info("clear_first=True，已清空 project_id=%s 的旧需求", project_id)

        sql = """
            INSERT INTO Requirement
                (req_id, project_id, doc_id, title, description, acceptance,
                 req_type, status, source_location, is_ambiguous)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        for r in reqs:
            rid = r.get("req_id")
            if not rid:
                skipped += 1
                logger.warning("跳过无 req_id 的需求: %s", r.get("title"))
                continue

            # 模糊词标记
            blob = f"{r.get('title') or ''} {r.get('description') or ''}"
            is_amb = 1 if has_ambiguous(blob) else 0
            if is_amb:
                ambiguous += 1

            # 段落定位
            loc = None
            if para_index:
                loc = (
                    locate_requirement(r.get("description", ""), para_index)
                    or locate_requirement(r.get("title", ""), para_index)
                )

            try:
                conn.execute(sql, (
                    rid,
                    project_id,
                    doc_id,
                    r.get("title") or "",
                    r.get("description") or "",
                    _to_acceptance_text(r.get("acceptance_criteria", [])),
                    _normalize_req_type(r.get("req_type")),
                    "未审核",
                    json.dumps(loc, ensure_ascii=False) if loc else None,
                    is_amb,
                ))
                saved += 1
            except Exception as e:
                skipped += 1
                logger.exception("写入 %s 失败: %s", rid, e)

        conn.commit()
    finally:
        conn.close()

    logger.info("保存完成: saved=%d skipped=%d ambiguous=%d", saved, skipped, ambiguous)
    return {"saved": saved, "skipped": skipped, "ambiguous": ambiguous}


# ---------- 查询 ----------
def get_requirements(project_id: int, status: Optional[str] = None) -> List[Dict]:
    """按项目查需求，可选按状态过滤。返回 list[dict]，acceptance/source_location 已解析。"""
    conn = get_connection()
    try:
        if status:
            cur = conn.execute(
                "SELECT * FROM Requirement WHERE project_id=? AND status=? ORDER BY req_id",
                (project_id, status),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM Requirement WHERE project_id=? ORDER BY req_id",
                (project_id,),
            )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    # 反序列化 JSON 字段
    for row in rows:
        for key in ("acceptance", "source_location"):
            if row.get(key):
                try:
                    row[key] = json.loads(row[key])
                except (json.JSONDecodeError, TypeError):
                    pass
    return rows


def count_requirements(project_id: int) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM Requirement WHERE project_id=?", (project_id,)
        )
        return cur.fetchone()[0]
    finally:
        conn.close()



# ---------- 状态流转（FR-3.4） ----------
ALLOWED_STATUS = {"未审核", "已确认"}

def update_status(req_id: str, new_status: str) -> bool:
    """切换需求状态，只允许 未审核 <-> 已确认。返回是否更新成功。"""
    if new_status not in ALLOWED_STATUS:
        raise ValueError(f"非法状态: {new_status}")
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE Requirement SET status=?, updated_at=CURRENT_TIMESTAMP WHERE req_id=?",
            (new_status, req_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()