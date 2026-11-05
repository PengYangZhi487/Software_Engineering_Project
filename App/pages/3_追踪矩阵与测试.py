# App/pages/3_追踪矩阵与测试.py
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from App.ui_theme import inject_style, guard_login, sidebar_footer

st.set_page_config(page_title="追踪矩阵与测试", layout="wide")
inject_style()
guard_login()
sidebar_footer()

st.title("🔗 追踪矩阵与测试用例")
st.info("⏳ 待实现：依赖 `case_service.py`（LLM 用例生成）与 `track_service.py`（覆盖率）")
st.markdown("""
**上线后页面功能**：
- 选择已确认需求 → 生成正常 / 异常 / 边界三类用例
- 用例审核（前置条件、步骤、预期结果可编辑）
- 需求 × 用例矩阵视图（勾选建立 / 解除关联）
- 自动计算覆盖率
""")