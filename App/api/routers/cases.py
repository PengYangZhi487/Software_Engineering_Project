"""P5：测试用例生成与审核。

POST /api/projects/{project_id}/cases/generate  为已确认需求批量生成候选
GET  /api/projects/{project_id}/cases           用例列表（按状态 / 类型统计）
PATCH /api/cases/{tc_id}                        审核 / 驳回 / 撤回

约定：
- 只对「已确认」需求生成，可勾选子集；
- 生成结果一律 `已生成`，审核由人做；
- replace=true 时先清空选中需求的旧用例（含关联记录）。
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Header, HTTPException

from App.api import repository
from App.api.schemas import (
    CaseGenerateRequest,
    CaseGenerateResult,
    CaseListOut,
    CaseStatusUpdate,
    TestCaseOut,
)
from App.services import case_service, llm_service, req_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cases"])


def _to_out(row: dict) -> TestCaseOut:
    return TestCaseOut(
        tc_id=int(row["tc_id"]),
        req_id=row.get("req_id"),
        title=row.get("title") or "",
        preconditions=row.get("preconditions") or [],
        steps=row.get("steps") or [],
        expected_result=row.get("expected_result") or "",
        test_type=row.get("test_type") or "normal",
        status=row.get("status") or "已生成",
    )


@router.get(
    "/projects/{project_id}/cases",
    response_model=CaseListOut,
    summary="项目测试用例列表",
)
def list_cases(project_id: int) -> CaseListOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    items = [_to_out(r) for r in repository.list_cases(project_id)]
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        by_type[item.test_type] = by_type.get(item.test_type, 0) + 1

    return CaseListOut(items=items, total=len(items), by_status=by_status, by_type=by_type)


@router.post(
    "/projects/{project_id}/cases/generate",
    response_model=CaseGenerateResult,
    summary="为已确认需求生成测试用例（大模型）",
)
def generate_cases(
    project_id: int,
    body: CaseGenerateRequest,
    x_deepseek_key: str | None = Header(
        None,
        alias="X-DeepSeek-Key",
        description="用户自己的 DeepSeek API Key；不传则回退到环境变量 DEEPSEEK_API_KEY",
    ),
) -> CaseGenerateResult:
    started = time.perf_counter()

    api_key = llm_service.resolve_api_key(x_deepseek_key)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="缺少 DeepSeek API Key：点页面右上角「设置」填入，或配置环境变量 DEEPSEEK_API_KEY",
        )

    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    all_reqs = req_service.get_requirements(project_id)
    confirmed = {r["req_id"]: r for r in all_reqs if r.get("status") == "已确认"}
    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="没有「已确认」的需求，先在需求库确认几条再生成用例",
        )

    if body.req_ids:
        picked = [rid for rid in body.req_ids if rid in confirmed]
        missing = [rid for rid in body.req_ids if rid not in confirmed]
        if not picked:
            raise HTTPException(
                status_code=400,
                detail=f"选中的需求不是已确认状态：{', '.join(missing[:5])}",
            )
    else:
        picked = list(confirmed)

    rows = [confirmed[rid] for rid in picked]
    logger.info("生成用例 project=%s 需求=%d 条 replace=%s", project_id, len(rows), body.replace)

    result = case_service.generate_cases(rows, api_key)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="用例生成失败：请检查「设置」里的 API Key 是否正确、账户是否有余额，稍后重试",
        )

    if body.replace:
        removed = repository.delete_cases_for_requirements(picked)
        if removed:
            logger.info("已清理 %d 条旧用例", removed)

    created = 0
    skipped = 0
    by_type: dict[str, int] = {}
    for case in result.cases:
        try:
            repository.insert_case(
                req_id=case.req_id,
                title=case.title,
                preconditions=case.preconditions,
                steps=case.steps,
                expected_result=case.expected_result,
                test_type=case.test_type,
            )
            created += 1
            by_type[case.test_type] = by_type.get(case.test_type, 0) + 1
        except Exception:  # pragma: no cover - 单条失败不影响整批
            skipped += 1
            logger.exception("写入用例失败：%s", case.title)

    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info("用例生成完成 created=%d skipped=%d 用时=%dms", created, skipped, elapsed)

    return CaseGenerateResult(
        created=created,
        skipped=skipped,
        by_type=by_type,
        elapsed_ms=elapsed,
        req_ids=picked,
        items=[_to_out(r) for r in repository.list_cases(project_id)],
    )


@router.patch(
    "/cases/{tc_id}",
    response_model=TestCaseOut,
    summary="审核 / 驳回 / 撤回用例",
)
def update_case(tc_id: int, body: CaseStatusUpdate) -> TestCaseOut:
    if body.status not in case_service.CASE_STATUS:
        raise HTTPException(
            status_code=422,
            detail=f"非法状态 {body.status}，只支持 {list(case_service.CASE_STATUS)}",
        )

    if not repository.update_case_status(tc_id, body.status):
        raise HTTPException(status_code=404, detail=f"用例 {tc_id} 不存在")

    row = repository.get_case(tc_id)
    if row is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail=f"用例 {tc_id} 不存在")
    return _to_out(row)
