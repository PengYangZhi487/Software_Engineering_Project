# App/pages/4_版本比对与影响.py
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from App.ui_theme import inject_style, guard_login, sidebar_footer

st.set_page_config(page_title="版本比对与影响", layout="wide")
inject_style()
guard_login()
sidebar_footer()

st.title("🔍 版本比对与影响分析")
st.info("⏳ 待实现：依赖 `diff_service.py`（difflib）与 `impact_service.py`")
st.markdown("""
**上线后页面功能**：
- 选择同项目两个文档版本 → difflib 段落比对
- 差异高亮（新增 / 删除 / 修改）
- 变更写入 `ChangeLog`
- 受影响用例清单（待复核）
""")