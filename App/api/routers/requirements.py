"""P3：需求抽取、列表与人工确认。

POST /api/projects/{project_id}/requirements/extract  调用 LLM 抽取并入库
GET  /api/projects/{project_id}/requirements          项目需求列表
PATCH /api/projects/{project_id}/requirements/{req_id}   确认 / 驳回 / 撤回

约定：
- 抽取是「候选」，一律以 未审核 入库；确认与否由人决定（AI 提候选、人做决策）。
- 编号由程序生成（CR-001…），不信任模型自己编的编号，避免重复。
- replace=false（默认）时追加写入并按项目 max+1 续号；replace=true 显式覆盖，
  会先清空该项目旧需求（破坏性，需调用方明确传参）。写入是单个事务：清空与
  插入要么全部生效，要么整体回滚。
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Header, HTTPException, Query

from App.api import repository
from App.api.schemas import (
    ExtractResult,
    RequirementCreate,
    RequirementListOut,
    RequirementOut,
    RequirementUpdate,
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
        priority=row.get("priority") or "中",
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
    replace: bool = Query(
        False, description="true=先清空该项目旧需求再写入（破坏性）；默认 false 追加续号"
    ),
    x_deepseek_key: str | None = Header(
        None,
        alias="X-DeepSeek-Key",
        description="用户自己的 DeepSeek API Key；不传则回退到环境变量 DEEPSEEK_API_KEY",
    ),
) -> ExtractResult:
    started = time.perf_counter()

    api_key = llm_service.resolve_api_key(x_deepseek_key)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="缺少 DeepSeek API Key：点页面右上角「设置」填入，或配置环境变量 DEEPSEEK_API_KEY",
        )

    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    target_doc = doc_id or repository.latest_document_id(project_id)
    if not target_doc:
        raise HTTPException(status_code=400, detail="项目里还没有文档，请先上传")

    doc_meta = repository.get_document(target_doc)
    if doc_meta is None:
        raise HTTPException(status_code=404, detail=f"文档 {target_doc} 不存在")
    if doc_meta.project_id != project_id:
        raise HTTPException(status_code=400, detail="该文档不属于当前项目")

    source = repository.get_document_source(target_doc)
    if not source or not source[0].strip():
        raise HTTPException(status_code=400, detail=f"文档 {target_doc} 没有可抽取的文本")
    text, para_index = source

    logger.info("开始抽取 project=%s doc=%s 字符=%d", project_id, target_doc, len(text))
    result = llm_service.extract_requirements(text, api_key)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="大模型调用失败：请检查「设置」里的 API Key 是否正确、账户是否有余额，稍后重试",
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

    rows = req_service.get_requirements(project_id)
    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info(
        "抽取完成 project=%s saved=%d skipped=%d ambiguous=%d 用时=%dms",
        project_id, stats["saved"], stats["skipped"], stats["ambiguous"], elapsed,
    )

    return ExtractResult(
        document=doc_meta,
        created=stats["saved"],
        skipped=stats["skipped"],
        ambiguous=stats["ambiguous"],
        replaced=replace,
        elapsed_ms=elapsed,
        items=[_to_out(r) for r in rows],
    )


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementOut,
    status_code=201,
    summary="手动新建需求",
)
def create_requirement(project_id: int, body: RequirementCreate) -> RequirementOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    req_id = f"CR-{repository.max_requirement_number(project_id) + 1:03d}"
    try:
        row = req_service.create_requirement(
            project_id,
            req_id,
            title=body.title,
            description=body.description,
            acceptance=body.acceptance,
            req_type=body.req_type,
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_out(row)


@router.patch(
    "/projects/{project_id}/requirements/{req_id}",
    response_model=RequirementOut,
    summary="编辑 / 确认 / 驳回需求",
)
def update_requirement(
    project_id: int, req_id: str, body: RequirementUpdate
) -> RequirementOut:
    try:
        row = req_service.update_requirement(
            project_id, req_id, body.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if row is None:
        raise HTTPException(status_code=404, detail=f"需求 {req_id} 不存在")
    return _to_out(row)
