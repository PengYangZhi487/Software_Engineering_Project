# App/pages/1_项目工作区.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from App.dao.db import get_connection
from App.ui_theme import inject_style, guard_login, sidebar_footer

st.set_page_config(page_title="项目工作区", layout="wide")
inject_style()
user = guard_login()
sidebar_footer()

st.title("📋 项目工作区")

# ---- 新建项目 ----
with st.container(border=True):
    st.subheader("➕ 新建项目")
    with st.form("new_proj", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        name = c1.text_input("项目名称")
        desc = c2.text_input("项目描述（可选）")
        if st.form_submit_button("创建项目", type="primary"):
            if not name.strip():
                st.error("项目名称不能为空")
            else:
                conn = get_connection()
                try:
                    conn.execute(
                        "INSERT INTO Project (project_name, description, owner_id) VALUES (?, ?, ?)",
                        (name.strip(), desc.strip() or None, user.get("user_id")),
                    )
                    conn.commit()
                    st.success(f"项目「{name}」创建成功")
                    st.rerun()
                finally:
                    conn.close()

# ---- 项目列表 ----
conn = get_connection()
try:
    rows = [dict(r) for r in conn.execute(
        """SELECT p.*, 
                  (SELECT COUNT(*) FROM Requirement r WHERE r.project_id=p.project_id) AS req_count,
                  (SELECT COUNT(*) FROM Requirement r WHERE r.project_id=p.project_id AND r.status='已确认') AS confirmed
             FROM Project p ORDER BY p.created_at DESC"""
    ).fetchall()]
finally:
    conn.close()

st.markdown(f"### 项目列表（{len(rows)}）")
if not rows:
    st.info("还没有项目，先创建一个吧")
    st.stop()

pid_now = st.session_state.get("current_project_id")

cols = st.columns(2)
for i, r in enumerate(rows):
    with cols[i % 2]:
        with st.container(border=True):
            is_cur = " ✅" if r["project_id"] == pid_now else ""
            st.markdown(f"#### #{r['project_id']} {r['project_name']}{is_cur}")
            if r["description"]:
                st.caption(r["description"])
            m1, m2 = st.columns(2)
            m1.metric("需求数", r["req_count"])
            m2.metric("已确认", r["confirmed"])
            if r["project_id"] != pid_now:
                if st.button("选为当前项目", key=f"sel_{r['project_id']}", use_container_width=True):
                    st.session_state.current_project_id = r["project_id"]
                    st.rerun()