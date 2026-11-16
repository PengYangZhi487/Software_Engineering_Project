import os
import json
from dotenv import load_dotenv  # 导入 dotenv 的加载函数
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from typing import List
from docx import Document

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY") 

# 检查一下有没有读到 Key
if not API_KEY:
    print("❌ 错误：没有读取到 API Key，请检查 .env 文件是否存在！")
    exit()

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# --- P4 的用例数据结构 ---
class TestCase(BaseModel):
    tc_id: str = Field(description="测试用例编号，如 TC-001")
    req_id: str = Field(description="关联的需求编号")
    title: str = Field(description="测试用例标题")
    preconditions: str = Field(description="前置条件")
    steps: List[str] = Field(description="操作步骤列表")
    expected_result: str = Field(description="预期结果")
    test_type: str = Field(description="类型：normal(正常), exception(异常), boundary(边界)")

# --- 假装我们有一个 Word 文档 (P1) ---
# 我们在本地生成一个临时的测试文档
doc = Document()
doc.add_paragraph("REQ-001：系统应允许学生在规定时间内选课。")
doc.add_paragraph("REQ-002：系统应快速响应学生的选课请求，不能卡顿。")
doc.save("mock_requirements.docx")

print("✅ P1 验证：正在读取 Word 文档...")
document = Document("mock_requirements.docx")
full_text = "\n".join([para.text for para in document.paragraphs])
print(f"读取到的文本：\n{full_text}\n")

# --- P3 规则检查 ---
print("🔍 P3 验证：规则引擎检查模糊词...")
vague_words = ["快速", "尽快", "良好", "适当", "及时"]
for para in document.paragraphs:
    for word in vague_words:
        if word in para.text:
            print(f"⚠️ 警告：发现模糊表达 '{word}' -> 原文：{para.text}")

# --- P4 用例生成 ---
print("\n🤖 P4 验证：生成测试用例...")
prompt = f"""
你是一个测试工程师。请根据以下需求生成 1 个边界测试用例。
严格按以下 JSON 格式输出：
{{
  "test_cases": [
    {{
      "tc_id": "TC-001",
      "req_id": "REQ-001",
      "title": "测试标题",
      "preconditions": "前置条件",
      "steps": ["步骤1", "步骤2"],
      "expected_result": "预期结果",
      "test_type": "boundary"
    }}
  ]
}}
需求文本：
{full_text}
"""

try:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个只输出 JSON 的程序。"},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    raw_json = response.choices[0].message.content
    print(f"生成的用例 JSON:\n{raw_json}")
    
    # 简单校验一下
    data = json.loads(raw_json)
    if "test_cases" in data and len(data["test_cases"]) > 0:
        print("✅ 校验成功！可以生成可用的候选用例。")
except Exception as e:
    print(f"❌ 生成失败: {e}")