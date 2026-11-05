# test_file/hld_test/rename_project.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from App.dao.db import get_connection

conn = get_connection()
try:
    cur = conn.execute(
        "UPDATE Project SET project_name=?, description=? WHERE project_id=?",
        ("校园选课系统 V1", "RATGP 演示项目", 1),
    )
    conn.commit()
    print(f"已更新 {cur.rowcount} 行")
    # 查回来确认
    row = conn.execute(
        "SELECT project_id, project_name, description FROM Project WHERE project_id=1"
    ).fetchone()
    print(dict(row))
finally:
    conn.close()