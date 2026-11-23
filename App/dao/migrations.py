"""一次性数据库迁移：Requirement 主键从 req_id 改为自增 id。

旧结构的问题
------------
``Requirement.req_id`` 是全局主键，但编号是按项目从 CR-001 生成的。
第二个项目再生成 CR-001 时会撞主键，整批 INSERT 失败（被吞成 skipped），
表现为“抽取成功但 0 条入库”。

新结构
------
- ``Requirement.id`` 自增主键；
- ``req_id`` 只在项目内唯一：``UNIQUE(project_id, req_id)``；
- 子表 ``TestCase`` / ``RequirementTestLink`` / ``ChangeLog`` 增加 ``project_id``，
  外键改为引用复合唯一键 ``(project_id, req_id)``。

迁移是幂等的：新表已经有 ``id`` 列时直接返回。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_NEW_REQUIREMENT = """
    CREATE TABLE Requirement_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        req_id TEXT NOT NULL,
        project_id INTEGER NOT NULL,
        doc_id INTEGER,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        acceptance TEXT,
        req_type TEXT DEFAULT 'functional',
        priority TEXT DEFAULT '中',
        status TEXT DEFAULT '未审核',
        source_location TEXT,
        is_ambiguous INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        UNIQUE(project_id, req_id),
        FOREIGN KEY(project_id) REFERENCES Project(project_id),
        FOREIGN KEY(doc_id) REFERENCES Document(doc_id)
    )
"""

_NEW_TESTCASE = """
    CREATE TABLE TestCase_new (
        tc_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        req_id TEXT,
        title TEXT NOT NULL,
        preconditions TEXT,
        steps TEXT,
        expected_result TEXT NOT NULL,
        test_type TEXT NOT NULL,
        status TEXT DEFAULT '已生成',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY(project_id, req_id) REFERENCES Requirement(project_id, req_id)
    )
"""

_NEW_LINK = """
    CREATE TABLE RequirementTestLink_new (
        link_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        req_id TEXT NOT NULL,
        tc_id INTEGER NOT NULL,
        link_source TEXT DEFAULT '人工',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id, req_id) REFERENCES Requirement(project_id, req_id),
        FOREIGN KEY(tc_id) REFERENCES TestCase(tc_id),
        UNIQUE(project_id, req_id, tc_id)
    )
"""

_NEW_CHANGELOG = """
    CREATE TABLE ChangeLog_new (
        change_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        req_id TEXT NOT NULL,
        old_content TEXT,
        new_content TEXT,
        change_type TEXT,
        version TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id, req_id) REFERENCES Requirement(project_id, req_id)
    )
"""


def _columns(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_requirement_priority(conn) -> bool:
    """给已经迁移到自增主键、但还没有 priority 列的库补列。"""
    if "priority" in _columns(conn, "Requirement"):
        return False
    conn.execute("ALTER TABLE Requirement ADD COLUMN priority TEXT DEFAULT '中'")
    conn.commit()
    logger.warning("Requirement 已补列 priority")
    print("[migrate] Requirement 已补列: priority")
    return True


def migrate_requirement_pk(conn) -> bool:
    """把旧库迁移到新结构；已迁移则返回 False。"""
    if "id" in _columns(conn, "Requirement"):
        return False

    logger.warning("检测到旧版 Requirement 主键（req_id TEXT PRIMARY KEY），开始迁移……")

    conn.commit()  # 清掉之前建表可能留下的隐式事务
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")

        conn.execute(_NEW_REQUIREMENT)
        conn.execute(
            """
            INSERT INTO Requirement_new
                (req_id, project_id, doc_id, title, description, acceptance,
                 req_type, status, source_location, is_ambiguous, created_at, updated_at)
            SELECT req_id, project_id, doc_id, title, description, acceptance,
                   COALESCE(req_type, 'functional'), status, source_location, is_ambiguous,
                   created_at, updated_at
            FROM Requirement
            """
        )

        # 子表用旧 req_id 反查 project_id（旧库 req_id 全局唯一，JOIN 唯一）
        conn.execute(_NEW_TESTCASE)
        conn.execute(
            """
            INSERT INTO TestCase_new
                (tc_id, project_id, req_id, title, preconditions, steps,
                 expected_result, test_type, status, created_at, updated_at)
            SELECT tc.tc_id, r.project_id, tc.req_id, tc.title, tc.preconditions, tc.steps,
                   tc.expected_result, tc.test_type, tc.status, tc.created_at, tc.updated_at
            FROM TestCase tc
            LEFT JOIN Requirement r ON r.req_id = tc.req_id
            """
        )

        conn.execute(_NEW_LINK)
        conn.execute(
            """
            INSERT INTO RequirementTestLink_new
                (link_id, project_id, req_id, tc_id, link_source, created_at)
            SELECT l.link_id, r.project_id, l.req_id, l.tc_id, l.link_source, l.created_at
            FROM RequirementTestLink l
            LEFT JOIN Requirement r ON r.req_id = l.req_id
            """
        )

        conn.execute(_NEW_CHANGELOG)
        conn.execute(
            """
            INSERT INTO ChangeLog_new
                (change_id, project_id, req_id, old_content, new_content,
                 change_type, version, timestamp)
            SELECT cl.change_id, r.project_id, cl.req_id, cl.old_content, cl.new_content,
                   cl.change_type, cl.version, cl.timestamp
            FROM ChangeLog cl
            LEFT JOIN Requirement r ON r.req_id = cl.req_id
            """
        )

        # 先拆子表再拆父表，然后统一改名
        conn.execute("DROP TABLE RequirementTestLink")
        conn.execute("DROP TABLE TestCase")
        conn.execute("DROP TABLE ChangeLog")
        conn.execute("DROP TABLE Requirement")
        conn.execute("ALTER TABLE Requirement_new RENAME TO Requirement")
        conn.execute("ALTER TABLE TestCase_new RENAME TO TestCase")
        conn.execute("ALTER TABLE RequirementTestLink_new RENAME TO RequirementTestLink")
        conn.execute("ALTER TABLE ChangeLog_new RENAME TO ChangeLog")

        # AUTOINCREMENT 的计数器跟着表名走，重建后校准一遍
        for table, column in (
            ("Requirement", "id"),
            ("TestCase", "tc_id"),
            ("RequirementTestLink", "link_id"),
            ("ChangeLog", "change_id"),
        ):
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
            conn.execute(
                f"INSERT INTO sqlite_sequence (name, seq) "
                f"SELECT ?, COALESCE(MAX({column}), 0) FROM {table}",
                (table,),
            )

        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"迁移后外键检查失败（前 5 条）：{violations[:5]}")

        conn.commit()

        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("Requirement", "TestCase", "RequirementTestLink", "ChangeLog")
        }
        logger.warning("迁移完成：%s", counts)
        print(f"[migrate] Requirement 主键已改为自增 id，数据：{counts}")
        return True

    except Exception:
        conn.rollback()
        logger.exception("迁移失败，已回滚，旧库结构保持不变")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
