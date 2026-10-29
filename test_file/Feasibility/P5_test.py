import sqlite3
import difflib
import json

# 1. 连接数据库（这会在本地生成一个 test.db 文件）
conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# 2. 建表：需求表 和 用例表 和 关联表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS requirements (
        req_id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        version TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS test_cases (
        tc_id TEXT PRIMARY KEY,
        req_id TEXT,
        description TEXT
    )
''')
# 清空旧数据，方便重复测试
cursor.execute('DELETE FROM requirements')
cursor.execute('DELETE FROM test_cases')

# 3. 插入 Mock 数据（模拟你 P2 提取出来的需求，以及你手动建的用例）
requirements_data = [
    ('REQ-001', '选课时间限制', '系统应允许学生在规定时间内选课', 'V1.0'),
    ('REQ-002', '课程人数上限', '课程人数达到50人时禁止选课', 'V1.0'),
    ('REQ-003', '快速响应', '系统应快速响应', 'V1.0')
]
test_cases_data = [
    ('TC-001', 'REQ-001', '在规定时间内选课成功'),
    ('TC-002', 'REQ-002', '第50人禁止选课'),
    ('TC-003', 'REQ-002', '两人抢最后名额'),
    # 注意：REQ-003 故意没有用例，用来测试覆盖率
]

cursor.executemany('INSERT INTO requirements VALUES (?, ?, ?, ?)', requirements_data)
cursor.executemany('INSERT INTO test_cases VALUES (?, ?, ?)', test_cases_data)
conn.commit()

print("✅ 数据库初始化完成，数据已插入。")

# 4. P5 核心任务一：计算覆盖率
cursor.execute('''
    SELECT COUNT(DISTINCT req_id) FROM test_cases 
    WHERE req_id IN (SELECT req_id FROM requirements)
''')
linked_reqs = cursor.fetchone()[0] # 有关联用例的需求数量
cursor.execute('SELECT COUNT(*) FROM requirements')
total_reqs = cursor.fetchone()[0] # 总需求数量

coverage = (linked_reqs / total_reqs) * 100
print(f"📊 需求测试关联覆盖率: {coverage:.2f}% ({linked_reqs}/{total_reqs})")

# 5. P5 核心任务二：版本比对与影响分析
print("\n--- 模拟需求变更 ---")
old_req_002 = "课程人数达到50人时禁止选课"
new_req_002 = "课程人数达到60人时禁止选课" # 容量从 50 改成 60

# 用 difflib 比对差异
matcher = difflib.SequenceMatcher(None, old_req_002, new_req_002)
diff = list(matcher.get_opcodes())
print(f"旧版本: {old_req_002}")
print(f"新版本: {new_req_002}")

changed_req_id = None
for tag, i1, i2, j1, j2 in diff:
    if tag != 'equal':
        print(f"🔍 发现变更: 把 '{old_req_002[i1:i2]}' 改为了 '{new_req_002[j1:j2]}'")
        changed_req_id = 'REQ-002'

# 6. P5 核心任务三：查询受影响用例
if changed_req_id:
    print(f"\n⚠️ 需求 {changed_req_id} 发生变更，以下测试用例需要复核：")
    cursor.execute('SELECT tc_id, description FROM test_cases WHERE req_id = ?', (changed_req_id,))
    affected_tcs = cursor.fetchall()
    for tc in affected_tcs:
        print(f"  -> {tc[0]}: {tc[1]}")

conn.close()