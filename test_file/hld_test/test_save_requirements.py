# test_file/hld_test/test_save_requirements.py
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from App.dao.db import get_connection, init_db
from App.services.doc_service import parse_docx
from App.services.llm_service import extract_requirements
from App.services.req_service import (
    save_requirements, get_requirements, count_requirements, clear_project_requirements,
)

DATASET = PROJECT_ROOT / "test_file" / "datasets" / "course_selection_v1.docx"
TEST_PROJECT_NAME = "__hld_test_project__"


def ensure_test_project() -> int:
    """确保存在一个测试项目，返回 project_id。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT project_id FROM Project WHERE project_name = ?",
            (TEST_PROJECT_NAME,),
        )
        row = cur.fetchone()
        if row:
            return row["project_id"]
        conn.execute(
            "INSERT INTO Project (project_name, description) VALUES (?, ?)",
            (TEST_PROJECT_NAME, "HLD 阶段入库联调用临时项目"),
        )
        conn.commit()
        pid = conn.execute(
            "SELECT project_id FROM Project WHERE project_name = ?",
            (TEST_PROJECT_NAME,),
        ).fetchone()["project_id"]
        print(f"[db] 新建测试项目 project_id={pid}")
        return pid
    finally:
        conn.close()


def main() -> int:
    # 1. 先跑一次 init_db 触发迁移（补 req_type 列）
    init_db()

    # 2. 准备数据
    if not DATASET.exists():
        print(f"数据集缺失: {DATASET}")
        return 1
    text, para_index = parse_docx(str(DATASET))
    result = extract_requirements(text)
    if result is None:
        print("LLM 提取失败")
        return 1
    print(f"[llm] 提取 {len(result.requirements)} 条需求")

    # 3. 项目准备
    pid = ensure_test_project()

    # 4. 入库（先清空后写入，避免重复）
    stats = save_requirements(
        project_id=pid,
        doc_id=None,
        requirements=result,
        para_index=para_index,
        clear_first=True,
    )
    print(f"[save] {stats}")

    # 5. 校验
    total = count_requirements(pid)
    print(f"[db] 项目 {pid} 当前需求数: {total}")
    assert total == 25, f"预期 25 条，实际 {total} 条"

    rows = get_requirements(pid)
    print(f"[query] 已读取 {len(rows)} 条")
    print("\n--- 抽检 3 条 ---")
    for rid in ("CR-001", "CR-015", "CR-025"):
        row = next(r for r in rows if r["req_id"] == rid)
        print(f"{rid}")
        print(f"  title       = {row['title']}")
        print(f"  req_type    = {row['req_type']}")
        print(f"  status      = {row['status']}")
        print(f"  is_ambiguous= {row['is_ambiguous']}")
        print(f"  acceptance  = {len(row['acceptance'])} 条")
        print(f"  source_loc  = {row['source_location']}")

    # 6. 断言：模糊需求 6 条
    amb_count = sum(1 for r in rows if r["is_ambiguous"] == 1)
    print(f"\n[check] 模糊需求标记 {amb_count} 条 (预期 6)")
    assert amb_count == 6, f"模糊需求数不对: {amb_count}"

    print("\n✅ 入库验证通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())