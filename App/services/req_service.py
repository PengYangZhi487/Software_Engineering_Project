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
    """清空指定项目的需求及其子数据（用于测试重建）。返回删除条数。"""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM Execution WHERE project_id = ? AND tc_id IN "
            "(SELECT tc_id FROM TestCase WHERE project_id = ?)",
            (project_id, project_id),
        )
        for table in ("ChangeLog", "RequirementTestLink", "TestCase"):
            conn.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
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
            # 重新抽取会替换需求编号，旧需求下的用例与关联必须先清掉，否则外键会拦。
            # 清空与随后的插入放在同一个事务里：任一步失败都整体回滚，不会出现
            # “旧数据已删、新数据只写了一半”的中间态。
            # Execution 引用 TestCase，必须先删，否则重新抽取会外键失败
            conn.execute(
                "DELETE FROM Execution WHERE project_id = ? AND tc_id IN "
                "(SELECT tc_id FROM TestCase WHERE project_id = ?)",
                (project_id, project_id),
            )
            for table in ("ChangeLog", "RequirementTestLink", "TestCase"):
                conn.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM Requirement WHERE project_id = ?", (project_id,))
            logger.info("clear_first=True，已清空 project_id=%s 的旧需求及其用例", project_id)

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

        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("保存需求失败，已回滚 project_id=%s", project_id)
        raise
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
# 已驳回 用于记录「人明确拒绝的 AI 候选」，保留行以便追溯，不物理删除。
ALLOWED_STATUS = {"未审核", "已确认", "已驳回"}
PRIORITIES = {"高", "中", "低"}
REQ_TYPES = {"functional", "non_functional"}


def create_requirement(
    project_id: int,
    req_id: str,
    *,
    title: str,
    description: str,
    acceptance: List[str],
    req_type: str,
    priority: str,
) -> Dict:
    """手动创建需求。编号由调用方按项目续号后传入。"""
    if req_type not in REQ_TYPES:
        raise ValueError(f"非法需求类型: {req_type}")
    if priority not in PRIORITIES:
        raise ValueError(f"非法优先级: {priority}")

    title = (title or "").strip()
    description = (description or "").strip()
    if not title or not description:
        raise ValueError("标题和描述不能为空")

    is_amb = 1 if has_ambiguous(f"{title} {description}") else 0
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO Requirement
                (req_id, project_id, doc_id, title, description, acceptance,
                 req_type, priority, status, source_location, is_ambiguous)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, '未审核', NULL, ?)
            """,
            (req_id, project_id, title, description,
             json.dumps(acceptance or [], ensure_ascii=False),
             req_type, priority, is_amb),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM Requirement WHERE project_id = ? AND req_id = ?",
            (project_id, req_id),
        ).fetchone()
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


def update_requirement(project_id: int, req_id: str, changes: Dict) -> Optional[Dict]:
    """按字段更新需求；只允许白名单字段，标题/描述变化时重算模糊标记。"""
    allowed = {"title", "description", "req_type", "priority", "acceptance", "status"}
    fields = {k: v for k, v in changes.items() if k in allowed and v is not None}

    if "status" in fields and fields["status"] not in ALLOWED_STATUS:
        raise ValueError(f"非法状态: {fields['status']}")
    if "req_type" in fields and fields["req_type"] not in REQ_TYPES:
        raise ValueError(f"非法需求类型: {fields['req_type']}")
    if "priority" in fields and fields["priority"] not in PRIORITIES:
        raise ValueError(f"非法优先级: {fields['priority']}")

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM Requirement WHERE project_id = ? AND req_id = ?",
            (project_id, req_id),
        ).fetchone()
        if row is None:
            return None
        current = dict(row)

        if "title" in fields:
            fields["title"] = fields["title"].strip()
            if not fields["title"]:
                raise ValueError("标题不能为空")
        if "description" in fields:
            fields["description"] = fields["description"].strip()
        if "acceptance" in fields:
            fields["acceptance"] = json.dumps(fields["acceptance"], ensure_ascii=False)

        if "title" in fields or "description" in fields:
            title = fields.get("title", current["title"])
            desc = fields.get("description", current["description"])
            fields["is_ambiguous"] = 1 if has_ambiguous(f"{title} {desc}") else 0

        if not fields:
            return None

        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE Requirement SET {sets}, updated_at = CURRENT_TIMESTAMP "
            "WHERE project_id = ? AND req_id = ?",
            [*fields.values(), project_id, req_id],
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM Requirement WHERE project_id = ? AND req_id = ?",
            (project_id, req_id),
        ).fetchone()
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


def update_status(project_id: int, req_id: str, new_status: str) -> bool:
    """切换需求状态（未审核 / 已确认 / 已驳回）。返回是否更新成功。"""
    if new_status not in ALLOWED_STATUS:
        raise ValueError(f"非法状态: {new_status}")
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE Requirement SET status=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE project_id=? AND req_id=?",
            (new_status, project_id, req_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()