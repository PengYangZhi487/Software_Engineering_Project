import os
import sqlite3
import hashlib

# 动态获取 App 目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 允许用环境变量覆盖（测试、联调时指向临时库）
DB_PATH = os.environ.get('RATGP_DB') or os.path.join(BASE_DIR, 'data', 'ratgp.db')

def get_connection():
    """获取数据库连接，并开启外键约束"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    # 让查询结果以字典形式返回，方便后续转 JSON
    conn.row_factory = sqlite3.Row
    return conn

def _migrate_requirement_add_req_type(conn):
    """如果 Requirement 表缺 req_type 列，补上（幂等）。"""
    cur = conn.execute("PRAGMA table_info(Requirement)")
    cols = {row["name"] for row in cur.fetchall()}
    if "req_type" in cols:
        return
    conn.execute(
        "ALTER TABLE Requirement ADD COLUMN req_type TEXT DEFAULT 'functional'"
    )
    conn.commit()
    print("[migrate] 已为 Requirement 表补列: req_type")

def init_db():
    """初始化数据库，建表，并写入默认管理员"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 建表 User
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'admin',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 建表 Project
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Project (
            project_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY(owner_id) REFERENCES User(user_id)
        )
    ''')
    
    # 3. 建表 Document
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Document (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            version TEXT NOT NULL,
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            content_text TEXT NOT NULL,
            para_index TEXT,
            file_path TEXT,
            FOREIGN KEY(project_id) REFERENCES Project(project_id)
        )
    ''')
    
    # 4. 建表 Requirement
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Requirement (
            req_id TEXT PRIMARY KEY,
            project_id INTEGER NOT NULL,
            doc_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            acceptance TEXT,
            status TEXT DEFAULT '未审核',
            source_location TEXT,
            is_ambiguous INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY(project_id) REFERENCES Project(project_id),
            FOREIGN KEY(doc_id) REFERENCES Document(doc_id)
        )
    ''')
    
    # 5. 建表 TestCase
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TestCase (
            tc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            req_id TEXT,
            title TEXT NOT NULL,
            preconditions TEXT,
            steps TEXT,
            expected_result TEXT NOT NULL,
            test_type TEXT NOT NULL,
            status TEXT DEFAULT '已生成',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY(req_id) REFERENCES Requirement(req_id)
        )
    ''')
    
    # 6. 建表 RequirementTestLink
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RequirementTestLink (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            req_id TEXT NOT NULL,
            tc_id INTEGER NOT NULL,
            link_source TEXT DEFAULT '人工',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(req_id) REFERENCES Requirement(req_id),
            FOREIGN KEY(tc_id) REFERENCES TestCase(tc_id),
            UNIQUE(req_id, tc_id)
        )
    ''')
    
    # 7. 建表 ChangeLog
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ChangeLog (
            change_id INTEGER PRIMARY KEY AUTOINCREMENT,
            req_id TEXT NOT NULL,
            old_content TEXT,
            new_content TEXT,
            change_type TEXT,
            version TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(req_id) REFERENCES Requirement(req_id)
        )
    ''')

    # === 新增：迁移已有表结构 ===
    _migrate_requirement_add_req_type(conn)
    
    # 写入默认管理员 (admin / 123456)
    # 密码哈希（简化版，仅作演示演示）
    pwd_hash = hashlib.sha256("123456".encode()).hexdigest()
    try:
        cursor.execute(
            "INSERT INTO User (username, password_hash, display_name) VALUES (?, ?, ?)",
            ("admin", pwd_hash, "系统管理员")
        )
        print("[init] 默认管理员 admin 创建成功。")
    except sqlite3.IntegrityError:
        pass # 已经存在则跳过
        
    conn.commit()
    conn.close()
    print(f"[init] 数据库初始化完成，路径: {DB_PATH}")

if __name__ == "__main__":
    init_db()