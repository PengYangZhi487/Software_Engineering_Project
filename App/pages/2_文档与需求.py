# App/pages/2_文档与需求.py
import sys, json, tempfile, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
from App.dao.db import get_connection
from App.services.doc_service import parse_document
from App.services.llm_service import extract_requirements
from App.services.req_service import get_requirements, save_requirements, update_status
from App.ui_theme import inject_style, guard_login, sidebar_footer

st.set_page_config(page_title="文档与需求", layout="wide")
inject_style()
guard_login()
sidebar_footer()

pid = st.session_state.get("current_project_id")
if not pid:
    st.warning("请先在「📋 项目工作区」选择当前项目")
    st.stop()

conn = get_connection()
try:
    proj = conn.execute("SELECT project_name FROM Project WHERE project_id=?", (pid,)).fetchone()
finally:
    conn.close()
proj_name = proj["project_name"] if proj else f"#{pid}"

st.title(f"📄 文档与需求 · {proj_name}")

tab_doc, tab_req = st.tabs(["📤 上传与提取", "📋 需求列表与管理"])

# ============ Tab 1：上传 + 提取 ============
with tab_doc:
    with st.container(border=True):
        st.subheader("上传需求文档")
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded = st.file_uploader("选择文档（.docx / .txt）", type=["docx", "txt"])
        with col2:
            version = st.text_input("版本号", value="V1")

    if uploaded:
        # 保存到临时文件解析
        suffix = Path(uploaded.name).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(uploaded.read())
        tmp.close()

        try:
            text, para_index = parse_document(tmp.name)
        except Exception as e:
            st.error(f"解析失败：{e}")
            st.stop()

        st.success(f"解析成功：{len(para_index)} 段，共 {len(text)} 字")

        with st.expander("段落预览（前 5 段）"):
            for p in para_index[:5]:
                st.code(f"[{p['para_no']}] {p['raw'][:80]}")

        if st.button("🤖 调用大模型提取需求", type="primary"):
            with st.spinner("正在调用 DeepSeek ..."):
                result = extract_requirements(text)

            if not result:
                st.error("LLM 提取失败，请检查网络或 Key")
            else:
                st.success(f"提取成功：{len(result.requirements)} 条需求")

                # 入库 Document
                conn = get_connection()
                try:
                    cur = conn.execute(
                        "INSERT INTO Document (project_id, filename, version, content_text, para_index) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (pid, uploaded.name, version, text, json.dumps(para_index, ensure_ascii=False)),
                    )
                    conn.commit()
                    doc_id = cur.lastrowid
                finally:
                    conn.close()

                # 入库 Requirement
                stats = save_requirements(
                    project_id=pid, doc_id=doc_id,
                    requirements=result, para_index=para_index,
                    clear_first=True,
                )
                st.json(stats)
                st.info("已写入数据库。切到「需求列表」页查看并确认。")

# ============ Tab 2：需求列表与管理 ============
with tab_req:
    rows = get_requirements(pid)
    if not rows:
        st.info("本项目暂无需求，请先在「上传与提取」页上传文档")
        st.stop()

    total = len(rows)
    confirmed = sum(1 for r in rows if r["status"] == "已确认")
    ambiguous = sum(1 for r in rows if r["is_ambiguous"] == 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("需求总数", total)
    c2.metric("已确认", confirmed)
    c3.metric("未审核", total - confirmed)
    c4.metric("模糊需求", ambiguous)

    # ---- 筛选 ----
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    status_filter = fc1.radio("状态", ["全部", "未审核", "已确认"], horizontal=True)
    only_amb = fc2.checkbox("只看模糊")
    req_type = fc3.selectbox("类型", ["全部", "functional", "non_functional"])

    filtered = rows
    if status_filter != "全部":
        filtered = [r for r in filtered if r["status"] == status_filter]
    if only_amb:
        filtered = [r for r in filtered if r["is_ambiguous"] == 1]
    if req_type != "全部":
        filtered = [r for r in filtered if r["req_type"] == req_type]

    # ---- 表格 ----
    table = pd.DataFrame([{
        "编号": r["req_id"],
        "标题": r["title"],
        "类型": r["req_type"],
        "状态": r["status"],
        "模糊": "⚠️" if r["is_ambiguous"] else "",
    } for r in filtered])
    st.dataframe(table, use_container_width=True, hide_index=True)

    # ---- 详情展开 ----
    st.markdown("---")
    st.subheader("需求详情")
    for r in filtered:
        loc = r.get("source_location") or {}
        label = f"{'⚠️ ' if r['is_ambiguous'] else ''}{r['req_id']} · {r['title']} · {r['status']}"
        with st.expander(label):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**类型**：`{r['req_type']}`　**状态**：`{r['status']}`")
                st.markdown(f"**描述**：{r['description']}")
                st.markdown("**验收条件**：")
                for i, ac in enumerate(r.get("acceptance") or [], 1):
                    st.markdown(f"{i}. {ac}")
            with col2:
                target = "已确认" if r["status"] == "未审核" else "未审核"
                btn_label = "✅ 确认" if target == "已确认" else "↩️ 撤回"
                if st.button(btn_label, key=f"st_{r['req_id']}", use_container_width=True):
                    update_status(r["req_id"], target)
                    st.rerun()
            if loc:
                st.markdown("**来源段落**：")
                st.code(f"para_no={loc.get('para_no')}  ratio={loc.get('ratio')}\n{loc.get('raw')}", language="text")
            if r["is_ambiguous"]:
                st.warning("命中模糊词，建议补充量化指标")