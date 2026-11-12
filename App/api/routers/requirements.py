"""P3：需求抽取、列表与人工确认。

POST /api/projects/{project_id}/requirements/extract  调用 LLM 抽取并入库
GET  /api/projects/{project_id}/requirements          项目需求列表
PATCH /api/requirements/{req_id}                      确认 / 驳回 / 撤回

约定：
- 抽取是「候选」，一律以 未审核 入库；确认与否由人决定（AI 提候选、人做决策）。
- 编号由程序生成（CR-001…），不信任模型自己编的编号，避免重复。
- replace=true 时会先清空该项目旧需求（重新抽取的场景），默认 true。
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Query

from App.api import repository
from App.api.schemas import (
    ExtractResult,
    RequirementListOut,
    RequirementOut,
    RequirementStatusUpdate,
    SourceLocation,
)
from App.services import llm_service, req_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["requirements"])


def _to_out(row: dict) -> RequirementOut:
    loc = row.get("source_location")
    return RequirementOut(
        req_id=row["req_id"],
        project_id=row["project_id"],
        title=row["title"],
        description=row["description"],
        req_type=row.get("req_type") or "functional",
        status=row["status"],
        acceptance=row.get("acceptance") or [],
        source_location=SourceLocation(**loc) if isinstance(loc, dict) else None,
        is_ambiguous=bool(row.get("is_ambiguous")),
    )


@router.get(
    "/projects/{project_id}/requirements",
    response_model=RequirementListOut,
    summary="项目需求列表",
)
def list_requirements(
    project_id: int,
    status: str | None = Query(None, description="未审核 / 已确认 / 已驳回"),
) -> RequirementListOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    rows = req_service.get_requirements(project_id, status)
    items = [_to_out(r) for r in rows]
    return RequirementListOut(
        items=items,
        total=len(items),
        confirmed=sum(1 for r in items if r.status == "已确认"),
        ambiguous=sum(1 for r in items if r.is_ambiguous),
    )


@router.post(
    "/projects/{project_id}/requirements/extract",
    response_model=ExtractResult,
    summary="从文档抽取需求（大模型）",
)
def extract_requirements(
    project_id: int,
    doc_id: int | None = Query(None, description="不传则用最新文档"),
    replace: bool = Query(True, description="true=先清空旧需求再写入"),
) -> ExtractResult:
    started = time.perf_counter()

    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    target_doc = doc_id or repository.latest_document_id(project_id)
    if not target_doc:
        raise HTTPException(status_code=400, detail="项目里还没有文档，请先上传")

    source = repository.get_document_source(target_doc)
    if not source or not source[0].strip():
        raise HTTPException(status_code=400, detail=f"文档 {target_doc} 没有可抽取的文本")
    text, para_index = source

    logger.info("开始抽取 project=%s doc=%s 字符=%d", project_id, target_doc, len(text))
    result = llm_service.extract_requirements(text)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="大模型抽取失败（检查 DEEPSEEK_API_KEY、网络或配额），可稍后重试",
        )

    base = 0 if replace else repository.max_requirement_number(project_id)
    payload = []
    for i, item in enumerate(result.requirements, start=1):
        data = item.model_dump()
        data["req_id"] = f"CR-{base + i:03d}"
        payload.append(data)

    stats = req_service.save_requirements(
        project_id=project_id,
        doc_id=target_doc,
        requirements=payload,
        para_index=para_index,
        clear_first=replace,
    )

    meta = repository.get_document(target_doc)
    if meta is None:  # pragma: no cover - 理论上不会发生
        raise HTTPException(status_code=500, detail="文档记录丢失")

    rows = req_service.get_requirements(project_id)
    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info(
        "抽取完成 project=%s saved=%d skipped=%d ambiguous=%d 用时=%dms",
        project_id, stats["saved"], stats["skipped"], stats["ambiguous"], elapsed,
    )

    return ExtractResult(
        document=meta,
        created=stats["saved"],
        skipped=stats["skipped"],
        ambiguous=stats["ambiguous"],
        replaced=replace,
        elapsed_ms=elapsed,
        items=[_to_out(r) for r in rows],
    )


@router.patch(
    "/requirements/{req_id}",
    response_model=RequirementOut,
    summary="确认 / 驳回 / 撤回需求",
)
def update_requirement(req_id: str, body: RequirementStatusUpdate) -> RequirementOut:
    if body.status not in req_service.ALLOWED_STATUS:
        raise HTTPException(
            status_code=422,
            detail=f"非法状态 {body.status}，只支持 {sorted(req_service.ALLOWED_STATUS)}",
        )

    if not req_service.update_status(req_id, body.status):
        raise HTTPException(status_code=404, detail=f"需求 {req_id} 不存在")

    row = repository.get_requirement(req_id)
    if row is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail=f"需求 {req_id} 不存在")
    return _to_out(row)
