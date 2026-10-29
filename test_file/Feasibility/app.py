import streamlit as st
import sqlite3
import difflib
from openai import OpenAI
import json

# 配置页面
st.set_page_config(page_title="需求追踪原型 P6", layout="wide")
st.title("🚀 需求分析与追踪辅助生成平台 (P6 原型)")

# 侧边栏配置 API
with st.sidebar:
    st.header("设置")
    api_key = st.text_input("输入 DeepSeek API Key", type="password")
    st.info("这是原型演示，数据存入本地 SQLite 数据库。")

# 主界面分栏
col1, col2 = st.columns(2)

# --- 左栏：需求提取与版本变更 ---
with col1:
    st.subheader("1. 需求输入与变更")
    req_text = st.text_area("输入需求文本（模拟上传文档）", "REQ-001：课程人数达到 50 人时禁止选课。", height=100)
    
    if st.button("解析并保存需求"):
        # 这里为了演示，我们直接模拟大模型提取成功后的结构化数据（省去网络调用时间）
        # 实际项目中，这里应该调用 P2 的 extract_requirements 函数
        st.success("✅ 提取成功！")
        
        # 存数据库
        conn = sqlite3.connect('demo.db')
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS reqs (id TEXT, text TEXT, version TEXT)')
        c.execute('DELETE FROM reqs')
        c.execute("INSERT INTO reqs VALUES ('REQ-001', '课程人数达到 50 人时禁止选课', 'V1.0')")
        conn.commit()
        conn.close()

    st.markdown("---")
    st.subheader("2. 模拟需求变更 (V1.0 -> V2.0)")
    new_req_text = st.text_input("变更后的需求", "课程人数达到 60 人时禁止选课")
    
    if st.button("比对变更并查影响"):
        old_text = "课程人数达到 50 人时禁止选课"
        matcher = difflib.SequenceMatcher(None, old_text, new_req_text)
        diff = list(matcher.get_opcodes())
        
        st.warning("⚠️ 检测到需求变更：REQ-001")
        for tag, i1, i2, j1, j2 in diff:
            if tag != 'equal':
                st.write(f"把 `{old_text[i1:i2]}` 改为了 `{new_req_text[j1:j2]}`")
        
        st.write("👉 **受影响的测试用例：** TC-001 (测试50人边界), TC-002 (测试两人抢名额)")

# --- 右栏：用例生成与覆盖率 ---
with col2:
    st.subheader("3. 测试用例管理")
    st.write("当前关联情况：")
    st.table([
        {"用例ID": "TC-001", "关联需求": "REQ-001", "描述": "测试50人边界"},
        {"用例ID": "TC-002", "关联需求": "REQ-001", "描述": "测试两人抢名额"},
        {"用例ID": "TC-003", "关联需求": "REQ-002", "描述": "选课时间测试"}
    ])
    
    st.markdown("---")
    st.subheader("4. 质量报告看板")
    st.metric(label="需求测试关联覆盖率", value="66.67%", delta="达标")
    
    st.write("**导出报告功能（占位）**")
    st.button("📥 导出 CSV 报告")