# App/app.py
import sys
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from App.dao.db import get_connection, init_db
from App.ui_theme import inject_style, sidebar_footer

st.set_page_config(page_title="RATGP 平台", page_icon="🧩", layout="wide")
inject_style()


@st.cache_resource
def _boot():
    init_db()
    return True


_boot()

for k, d in (("logged_in", False), ("user", None), ("current_project_id", None)):
    st.session_state.setdefault(k, d)


# ---- 登录校验 ----
def _verify(u: str, p: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT user_id, username, password_hash, display_name, role FROM User WHERE username=?",
            (u,),
        ).fetchone()
    finally:
        conn.close()
    if row and hashlib.sha256(p.encode()).hexdigest() == row["password_hash"]:
        return dict(row)
    return None


# ---------- 未登录：登录页 ----------
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    left, mid, right = st.columns([1, 1.2, 1])
    with mid:
        with st.container(border=True):
            st.markdown("### 🧩 RATGP 平台")
            st.caption("需求解析与测试用例生成")
            st.markdown("---")
            with st.form("login"):
                username = st.text_input("用户名", value="admin")
                password = st.text_input("密码", type="password", value="123456")
                if st.form_submit_button("登 录", type="primary", use_container_width=True):
                    user = _verify(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
            st.caption("演示账号：admin / 123456")
    st.stop()


# ---------- 已登录：欢迎页 ----------
user = st.session_state.user
sidebar_footer()

st.title("🧩 RATGP 平台")
st.caption("需求解析 · 测试用例生成 · 追踪矩阵 · 变更影响分析")

conn = get_connection()
try:
    p_count = conn.execute("SELECT COUNT(*) AS c FROM Project").fetchone()["c"]
    r_count = conn.execute("SELECT COUNT(*) AS c FROM Requirement").fetchone()["c"]
    c_count = conn.execute("SELECT COUNT(*) AS c FROM Requirement WHERE status='已确认'").fetchone()["c"]
    a_count = conn.execute("SELECT COUNT(*) AS c FROM Requirement WHERE is_ambiguous=1").fetchone()["c"]
    pid = st.session_state.current_project_id
    cur_name = "未选择"
    if pid:
        row = conn.execute("SELECT project_name FROM Project WHERE project_id=?", (pid,)).fetchone()
        if row:
            cur_name = row["project_name"]
finally:
    conn.close()

c1, c2, c3, c4 = st.columns(4)
c1.metric("项目数", p_count)
c2.metric("需求总数", r_count)
c3.metric("已确认", c_count)
c4.metric("模糊需求", a_count)

st.markdown("---")

if not pid:
    st.info("👉 点击左侧 **📋 项目工作区** 选择或创建一个项目")
else:
    with st.container(border=True):
        st.markdown(f"### 当前项目：**{cur_name}**")
        st.markdown("""
- 📄 **文档与需求**：上传 DOCX/TXT，调用大模型提取结构化需求，人工确认
- 🔗 **追踪矩阵与测试**（待补齐）：基于已确认需求生成用例
- 🔍 **版本比对与影响**（待补齐）：difflib 对比两版本文档
- 📊 **质量报告**：覆盖率统计与 CSV 导出
        """)

with st.expander("ℹ️ 平台功能说明"):
    st.markdown("""
    **Part A 平台功能**：需求解析、用例生成、追踪覆盖、变更影响、报告导出  
    **Part B 测试数据集**：校园选课系统需求说明书（25 条，含模糊/矛盾）
    """)