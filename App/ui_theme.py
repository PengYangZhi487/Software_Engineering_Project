# App/ui_theme.py
"""
统一视觉主题和通用 UI 组件。
每个页面顶部 import 并调用 inject_style()，样式即可生效。
"""
import streamlit as st

_CSS = """
<style>
/* ---- 全局 ---- */
.stApp {
    background: linear-gradient(135deg, #f0f4fb 0%, #e6edf9 100%);
    font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
h1 { color: #1e3a8a !important; letter-spacing: .5px; }
h2, h3 { color: #1e40af !important; }

/* ---- 卡片容器（用 st.container(border=True) 即可套用） ---- */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border-radius: 14px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 2px 10px rgba(30, 58, 138, 0.06) !important;
    padding: 6px 14px;
}

/* ---- 指标卡 ---- */
[data-testid="stMetric"] {
    background: #ffffff;
    border-radius: 12px;
    padding: 14px 18px;
    border-left: 4px solid #3b82f6;
    box-shadow: 0 2px 10px rgba(30, 58, 138, 0.08);
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-weight: 500; }
[data-testid="stMetricValue"] { color: #1e3a8a !important; font-weight: 700; }

/* ---- 按钮 ---- */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all .15s ease;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #1e40af) !important;
    border: none !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
}

/* ---- 侧边栏 ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%) !important;
}
[data-testid="stSidebar"] * { color: #e0e7ff !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255, 255, 255, 0.12) !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    color: #ffffff !important;
}

/* ---- 表格 ---- */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ---- 表单/输入框 ---- */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    border-radius: 8px !important;
}

/* ---- 提示框 ---- */
[data-testid="stAlert"] { border-radius: 10px; }

/* ---- 隐藏 Streamlit 默认页脚 ---- */
footer { visibility: hidden; }
</style>
"""


def inject_style():
    """在每个页面顶部调用一次。Streamlit 会自动去重相同内容，多次调用无副作用。"""
    st.markdown(_CSS, unsafe_allow_html=True)


def guard_login() -> dict:
    """未登录就停在当前页，返回当前用户字典。"""
    if not st.session_state.get("logged_in"):
        st.warning("🔒 请先回主页登录")
        st.stop()
    return st.session_state.get("user") or {}


def sidebar_footer():
    """在侧边栏底部放用户信息 + 退出按钮。"""
    user = st.session_state.get("user") or {}
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**👤 {user.get('display_name') or user.get('username') or '未登录'}**")
        st.caption(f"角色：{user.get('role', '-')}")
        if st.button("🚪 退出登录", use_container_width=True, key="_sidebar_logout"):
            for k in ("logged_in", "user", "current_project_id"):
                st.session_state.pop(k, None)
            st.switch_page("app.py")