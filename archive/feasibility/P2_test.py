import os
import json
from dotenv import load_dotenv  # 导入 dotenv 的加载函数
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from typing import List

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 检查一下有没有读到 Key
if not API_KEY:
    print("❌ 错误：没有读取到 API Key，请检查 .env 文件是否存在！")
    exit()

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

class Requirement(BaseModel):
    req_id: str = Field(description="需求编号，如 REQ-001")
    title: str = Field(description="需求标题，简短概括")
    description: str = Field(description="需求描述详情")
    req_type: str = Field(description="需求类型，只能是 functional 或 non-functional")
    acceptance_criteria: List[str] = Field(description="验收条件列表，至少1条")

class RequirementList(BaseModel):
    requirements: List[Requirement]

test_text = """
系统应允许学生在规定时间内选课，并在课程人数达到上限时禁止继续选课。
系统应快速响应学生的选课请求。
"""

def extract_requirements(text: str, max_retries=3):
    # 绝杀：把 Pydantic 定义的 JSON Schema 提取出来
    schema_str = json.dumps(RequirementList.model_json_schema(), ensure_ascii=False)
    # 正确的完美示例，逼大模型“抄作业”
    example_output = """
    {
      "requirements": [
        {
          "req_id": "REQ-001",
          "title": "课程人数限制",
          "description": "每门课程最多容纳50名学生",
          "req_type": "functional",
          "acceptance_criteria": [
            "当前人数小于50时允许选课",
            "当前人数达到50时拒绝新选课"
          ]
        }
      ]
    }
    """

    base_prompt = f"""
    你是一个专业的软件需求分析师。请从文本中提取结构化需求。
    
    【极度重要】你必须严格使用以下字段名，绝对不允许更改！
    正确格式示例：
    {example_output}

    请根据上述示例的格式，提取以下文本中的需求：
    {text}
    """
    
    current_prompt = base_prompt
    
    for attempt in range(max_retries):
        print(f"\n--- 第 {attempt + 1} 次调用 ---")
        try:
            # 将 temperature 稍微调高到 0.3，打破它的默认输出死循环
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个只会输出合法 JSON 的程序。绝对不要输出 Markdown 代码块标记。必须严格遵守用户提供的 JSON Schema。"},
                    {"role": "user", "content": current_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3 
            )
            
            raw_json = response.choices[0].message.content
            print(f"大模型原始输出:\n{raw_json}")
            
            parsed_data = json.loads(raw_json)
            validated_data = RequirementList(**parsed_data)
            
            print("✅ 校验成功！数据结构符合要求。")
            return validated_data
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {e}"
            print(f"❌ {error_msg}")
            current_prompt = base_prompt + f"\n\n注意：你上一次的输出格式错了。请严格按 Schema 输出 JSON。"
            
        except ValidationError as e:
            # 提取简短的报错信息
            error_msg = f"字段校验失败。你输出了错误的字段名！"
            print(f"❌ 数据结构校验失败:\n{e}")
            current_prompt = base_prompt + f"\n\n注意：你上一次的输出字段名完全错误！请仔细看 Schema，不要用 'id' 和 'type'，必须用 'req_id' 和 'req_type'。缺失的字段：title, acceptance_criteria 必须补上。"
            
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            
    print("⚠️ 达到最大重试次数，彻底失败。")
    return None

if __name__ == "__main__":
    result = extract_requirements(test_text)
    if result:
        print("\n--- 最终提取结果 ---")
        for req in result.requirements:
            print(f"[{req.req_id}] {req.title} ({req.req_type})")
            print(f"  描述: {req.description}")
            print(f"  验收条件: {req.acceptance_criteria}")