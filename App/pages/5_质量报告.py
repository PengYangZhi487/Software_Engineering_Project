# App/pages/5_质量报告.py
import sys, io, csv
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from App.services.req_service import get_requirements
from App.ui_theme import inject_style, guard_login, sidebar_footer

st.set_page_config(page_title="质量报告", layout="wide")
inject_style()
guard_login()
sidebar_footer()

pid = st.session_state.get("current_project_id")
if not pid:
    st.warning("请先选择项目")
    st.stop()

st.title("📊 质量报告")

rows = get_requirements(pid)
total = len(rows)
confirmed = sum(1 for r in rows if r["status"] == "已确认")
amb = sum(1 for r in rows if r["is_ambiguous"] == 1)
types = {}
for r in rows:
    types[r["req_type"]] = types.get(r["req_type"], 0) + 1

c1, c2, c3, c4 = st.columns(4)
c1.metric("需求总数", total)
c2.metric("已确认", confirmed)
c3.metric("模糊需求", amb)
c4.metric("覆盖率", "N/A", help="待用例生成模块就绪后计算")

st.markdown("### 类型分布")
st.dataframe(
    [{"类型": k, "数量": v} for k, v in types.items()],
    use_container_width=True, hide_index=True,
)

# ---- 导出 CSV ----
st.markdown("### 导出")
if st.button("📥 导出需求清单 CSV", type="primary"):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["req_id", "title", "description", "req_type", "status", "is_ambiguous", "source_para"])
    for r in rows:
        loc = r.get("source_location") or {}
        writer.writerow([
            r["req_id"], r["title"], r["description"], r["req_type"],
            r["status"], r["is_ambiguous"], loc.get("para_no", ""),
        ])
    st.download_button(
        "⬇️ 点击下载",
        data=buf.getvalue().encode("utf-8-sig"),
        file_name=f"requirements_project{pid}.csv",
        mime="text/csv",
    )