"""P5：测试用例生成（大模型只提候选，schema 与引用关系由程序校验）。

约定：
- 只接受「已确认」需求；
- req_id 必须来自给定集合，模型自己编的编号一律丢弃；
- 正常 / 异常 / 边界三类，边界值要求具体（49/50/51 这种）；
- 生成结果以「已生成」入库，审核由人完成。
"""
from __future__ import annotations

import json
import logging
from typing import Iterable, Literal

from pydantic import BaseModel, Field, ValidationError

from App.services.llm_service import get_client

logger = logging.getLogger(__name__)

CASE_STATUS = ("已生成", "已审核", "已驳回", "已执行")
CASE_TYPES = ("normal", "abnormal", "boundary")


class GeneratedCase(BaseModel):
    req_id: str = Field(description="必须是给定需求编号之一")
    title: str = Field(description="用例标题，一句话说明场景")
    preconditions: list[str] = Field(default_factory=list, description="前置条件")
    steps: list[str] = Field(description="操作步骤，至少 1 步")
    expected_result: str = Field(description="预期结果")
    test_type: Literal["normal", "abnormal", "boundary"]


class GeneratedCaseList(BaseModel):
    cases: list[GeneratedCase]


def _format_req(row: dict) -> str:
    acceptance = "；".join(row.get("acceptance") or []) or "（无）"
    return (
        f"{row.get('req_id')} | {row.get('title', '')} | "
        f"{row.get('description', '')} | 验收条件：{acceptance}"
    )


def generate_cases(
    requirements: Iterable[dict],
    api_key: str,
    max_retries: int = 2,
) -> GeneratedCaseList | None:
    reqs = list(requirements)
    if not reqs:
        return GeneratedCaseList(cases=[])

    schema = json.dumps(GeneratedCaseList.model_json_schema(), ensure_ascii=False)
    listing = "\n".join(_format_req(r) for r in reqs)

    base_prompt = f"""你是测试工程师，为下面这些「已确认」的需求设计测试用例。

要求：
1. 每条需求生成 2–4 条用例，必须同时覆盖正常、异常、边界三类中的至少两类；
2. 边界用例要给具体数值（例如容量 50 时测 49/50/51）；
3. req_id 必须原样使用给定编号，绝对不要自己编号；
4. 只输出 JSON，不要 Markdown 代码块，不要解释。

JSON Schema：
{schema}

需求列表（每行一条）：
{listing}
"""

    client = get_client(api_key)
    prompt = base_prompt

    for attempt in range(max_retries + 1):
        logger.info("用例生成第 %d/%d 次调用，需求 %d 条", attempt + 1, max_retries + 1, len(reqs))
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你只输出合法 JSON，严格遵守用户给出的 schema。",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw = response.choices[0].message.content
            parsed = GeneratedCaseList(**json.loads(raw))

            allowed = {r["req_id"] for r in reqs}
            valid = [c for c in parsed.cases if c.req_id in allowed]
            dropped = len(parsed.cases) - len(valid)
            if dropped:
                logger.warning("丢弃 %d 条引用了不存在需求的用例", dropped)
            if not valid:
                raise ValueError("没有任何用例引用了合法需求编号")

            return GeneratedCaseList(cases=valid)

        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            logger.warning("第 %d 次输出不合法：%s", attempt + 1, exc)
            prompt = (
                base_prompt
                + f"\n\n注意：上一次输出不合格（{str(exc)[:200]}）。请严格按 Schema 输出 JSON。"
            )
        except Exception as exc:  # 网络 / 额度问题，重试也不会好
            logger.exception("调用大模型失败：%s", exc)
            return None

    logger.error("用例生成重试耗尽")
    return None
