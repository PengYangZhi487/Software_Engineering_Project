# App/services/llm_service.py
"""LLM 客户端与需求抽取。

API Key 来源（优先级从高到低）：
1. 请求头 ``X-DeepSeek-Key`` —— 用户在界面右上角「设置」里填的，只存在浏览器会话里；
2. 系统环境变量 ``DEEPSEEK_API_KEY`` —— 开发者本机调试用。

两处都没有时由 API 层返回 401。项目不再读取 ``.env`` 文件，key 不落盘。
"""
import os
import json
import logging
from functools import lru_cache
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

ENV_KEY = "DEEPSEEK_API_KEY"


# ---------- Pydantic 模型：原样保留 ----------
class Requirement(BaseModel):
    req_id: str = Field(description="需求编号，如 REQ-001")
    title: str = Field(description="需求标题，简短概括")
    description: str = Field(description="需求描述详情")
    req_type: str = Field(description="需求类型，只能是 functional 或 non-functional")
    acceptance_criteria: List[str] = Field(description="验收条件列表，至少1条")

    @field_validator("req_type", mode="after")
    @classmethod
    def _normalize_req_type(cls, v: str) -> str:
        """把 non-functional / non functional / NonFunctional 统一成 non_functional。"""
        v_norm = (
            v.strip()
             .lower()
             .replace("-", "_")
             .replace(" ", "_")
        )
        if v_norm not in {"functional", "non_functional"}:
            raise ValueError(f"req_type 必须是 functional 或 non_functional，实际收到: {v!r}")
        return v_norm


class RequirementList(BaseModel):
    requirements: List[Requirement]


# ---------- 客户端：按 key 缓存，进程内复用连接 ----------
def resolve_api_key(header_key: str | None = None) -> str | None:
    """按「请求头 > 系统环境变量」取 key；都为空返回 None。"""
    for candidate in (header_key, os.getenv(ENV_KEY)):
        if candidate and candidate.strip():
            return candidate.strip()
    return None


@lru_cache(maxsize=8)
def _cached_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def get_client(api_key: str) -> OpenAI:
    """按调用方给的 key 取 client。

    只缓存在进程内存里（最多 8 个），进程结束即释放，写不到磁盘。
    不要把 key 打日志——这里只记录"是否已配置"。
    """
    key = (api_key or "").strip()
    if not key:
        raise ValueError("缺少 DeepSeek API Key")
    return _cached_client(key)


def _format_validation_error(e: ValidationError) -> str:
    """把 Pydantic 报错压成一句话，回灌给大模型。"""
    parts = []
    for err in e.errors()[:5]:
        loc = ".".join(str(x) for x in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


# ---------- 主函数 ----------
def extract_requirements(
    text: str,
    api_key: str,
    max_retries: int = 3,
) -> Optional[RequirementList]:
    """
    从需求文本中提取结构化需求。
    成功返回 RequirementList 对象；重试耗尽返回 None。
    api_key 由调用方传入（请求头或环境变量），本函数不读 .env。
    """
    schema_str = json.dumps(RequirementList.model_json_schema(), ensure_ascii=False)

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
    client = get_client(api_key)

    for attempt in range(max_retries):
        logger.info("LLM 需求提取第 %d/%d 次调用", attempt + 1, max_retries)
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system",
                     "content": "你是一个只会输出合法 JSON 的程序。绝对不要输出 Markdown 代码块标记。必须严格遵守用户提供的 JSON Schema。"},
                    {"role": "user", "content": current_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            raw_json = response.choices[0].message.content
            logger.debug("LLM 原始输出: %s", raw_json)

            parsed_data = json.loads(raw_json)
            validated_data = RequirementList(**parsed_data)

            logger.info("LLM 需求提取成功，共 %d 条", len(validated_data.requirements))
            return validated_data

        except json.JSONDecodeError as e:
            logger.warning("第 %d 次 JSON 解析失败: %s", attempt + 1, e)
            current_prompt = base_prompt + "\n\n注意：你上一次的输出格式错了。请严格按 Schema 输出 JSON。"

        except ValidationError as e:
            err_brief = _format_validation_error(e)
            logger.warning("第 %d 次字段校验失败: %s", attempt + 1, err_brief)
            current_prompt = (
                base_prompt
                + f"\n\n注意：你上一次输出字段有误（{err_brief}）。"
                + "请严格按 Schema 输出，不要用 'id'/'type'，必须用 'req_id'/'req_type'，并补全 title、acceptance_criteria。"
            )

        except Exception as e:
            logger.exception("第 %d 次调用出现未知错误: %s", attempt + 1, e)

    logger.error("LLM 需求提取重试耗尽，返回 None")
    return None