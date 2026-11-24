"""导入导出：让 Excel 当编辑器，软件当追溯层。

POST /api/projects/{pid}/requirements/import/xlsx   上传需求清单（multipart：file + mode）
POST /api/projects/{pid}/requirements/import/docx   上传 Word 需求表（multipart：file + mode）
POST /api/projects/{pid}/requirements/import/json   粘贴大模型输出（JSON 文本）
GET  /api/projects/{pid}/requirements/export?format=xlsx  导出可编辑需求清单
POST /api/projects/{pid}/cases/import/xlsx          上传用例清单
GET  /api/projects/{pid}/cases/export?format=xlsx   导出可编辑用例清单

约定：
- 导出的表头与导入完全一致，导出 → Excel 里改 → 导入回来即可；
- 需求编号：有且已存在则更新，没有则按项目 max+1 生成（模型给的编号不采信）；
- 用例编号：TC-xxx 存在则更新，否则新增（关联需求必须存在）；
- 单行失败只记 errors，不中断整批。
"""
from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile

from App.api import repository
from App.api.config import MAX_UPLOAD_BYTES
from App.api.schemas import ImportResult, RequirementImportJson
from App.services import req_service
from App.services.docx_import import parse_requirements_docx
from App.services.import_export import (
    XLSX_MIME,
    build_cases_workbook,
    build_requirements_workbook,
    extract_json_requirements,
    parse_cases_xlsx,
    parse_requirements_xlsx,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["import-export"])


def _ensure_project(project_id: int) -> None:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


def _mode(value: str) -> str:
    mode = (value or "append").strip().lower()
    if mode not in {"append", "replace"}:
        raise HTTPException(status_code=422, detail="mode 只支持 append / replace")
    return mode


async def _read_upload(file: UploadFile, suffix: str = ".xlsx") -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(suffix):
        detail = (
            "只支持 .docx；请上传带需求表格的 Word 文件（首行表头，一行一条需求）"
            if suffix == ".docx"
            else "只支持 .xlsx；可以先从页面导出一份清单，在 Excel 里改完再导入"
        )
        raise HTTPException(status_code=415, detail=detail)
    content = await file.read()
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 10 MB")
    return content


def _apply_requirements(project_id: int, rows: list[dict], mode: str) -> ImportResult:
    created = updated = skipped = 0
    errors: list[str] = []

    if mode == "replace":
        req_service.clear_project_requirements(project_id)

    next_no = repository.max_requirement_number(project_id) + 1
    for row in rows:
        try:
            title = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()
            if not title or not description:
                skipped += 1
                errors.append(f"第 {row.get('row', '?')} 行：标题或描述为空")
                continue

            req_id = (row.get("req_id") or "").strip()
            existing = repository.get_requirement(project_id, req_id) if req_id else None
            if existing is not None:
                req_service.update_requirement(
                    project_id,
                    req_id,
                    {
                        "title": title,
                        "description": description,
                        "req_type": row.get("req_type") or "functional",
                        "priority": row.get("priority") or "中",
                        "status": row.get("status") or "未审核",
                        "acceptance": row.get("acceptance") or [],
                    },
                )
                updated += 1
                continue

            new_id = req_id or f"CR-{next_no:03d}"
            while repository.get_requirement(project_id, new_id) is not None:
                next_no += 1
                new_id = f"CR-{next_no:03d}"

            req_service.create_requirement(
                project_id,
                new_id,
                title=title,
                description=description,
                acceptance=row.get("acceptance") or [],
                req_type=row.get("req_type") or "functional",
                priority=row.get("priority") or "中",
            )
            status = row.get("status") or "未审核"
            if status != "未审核":
                req_service.update_requirement(project_id, new_id, {"status": status})
            next_no += 1
            created += 1
        except Exception as exc:  # 单行失败不中断整批
            skipped += 1
            errors.append(f"第 {row.get('row', '?')} 行：{exc}")

    logger.info(
        "需求导入 project=%s mode=%s created=%d updated=%d skipped=%d",
        project_id, mode, created, updated, skipped,
    )
    return ImportResult(created=created, updated=updated, skipped=skipped, errors=errors[:20])


def _apply_cases(project_id: int, rows: list[dict]) -> ImportResult:
    created = updated = skipped = 0
    errors: list[str] = []

    for row in rows:
        try:
            req_id = (row.get("req_id") or "").strip()
            if not req_id or repository.get_requirement(project_id, req_id) is None:
                skipped += 1
                errors.append(f"第 {row.get('row', '?')} 行：关联需求 {req_id or '(空)'} 不存在")
                continue

            title = (row.get("title") or "").strip()
            expected = (row.get("expected_result") or "").strip()
            if not title or not expected:
                skipped += 1
                errors.append(f"第 {row.get('row', '?')} 行：用例标题或预期结果为空")
                continue

            tc_id = row.get("tc_id")
            existing = repository.get_case(tc_id) if tc_id else None
            if existing is not None and int(existing.get("project_id") or 0) == project_id:
                repository.update_case_fields(
                    tc_id,
                    {
                        "req_id": req_id,
                        "title": title,
                        "preconditions": json.dumps(row.get("preconditions") or [], ensure_ascii=False),
                        "steps": json.dumps(row.get("steps") or [], ensure_ascii=False),
                        "expected_result": expected,
                        "test_type": row.get("test_type") or "normal",
                        "status": row.get("status") or "已生成",
                    },
                )
                updated += 1
            else:
                repository.insert_case(
                    project_id=project_id,
                    req_id=req_id,
                    title=title,
                    preconditions=row.get("preconditions") or [],
                    steps=row.get("steps") or [],
                    expected_result=expected,
                    test_type=row.get("test_type") or "normal",
                    status=row.get("status") or "已生成",
                )
                created += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"第 {row.get('row', '?')} 行：{exc}")

    logger.info(
        "用例导入 project=%s created=%d updated=%d skipped=%d",
        project_id, created, updated, skipped,
    )
    return ImportResult(created=created, updated=updated, skipped=skipped, errors=errors[:20])


@router.post(
    "/projects/{project_id}/requirements/import/xlsx",
    response_model=ImportResult,
    summary="从 Excel 导入需求（可更新已有编号）",
)
async def import_requirements_xlsx(
    project_id: int,
    file: UploadFile = File(..., description="需求清单 .xlsx"),
    mode: str = Form("append", description="append 追加 / replace 先清空再导入"),
) -> ImportResult:
    _ensure_project(project_id)
    content = await _read_upload(file)
    try:
        rows = parse_requirements_xlsx(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析 Excel 失败：{exc}") from exc
    if not rows:
        raise HTTPException(status_code=400, detail="表格里没有可导入的行（第一行应为表头）")
    return _apply_requirements(project_id, rows, _mode(mode))


@router.post(
    "/projects/{project_id}/requirements/import/docx",
    response_model=ImportResult,
    summary="从 Word 需求表导入需求（可更新已有编号）",
)
async def import_requirements_docx(
    project_id: int,
    file: UploadFile = File(..., description="需求表 .docx（首行表头）"),
    mode: str = Form("append", description="append 追加 / replace 先清空再导入"),
) -> ImportResult:
    _ensure_project(project_id)
    content = await _read_upload(file, suffix=".docx")
    try:
        rows = parse_requirements_docx(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析 Word 失败：{exc}") from exc
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Word 里没有可导入的需求表（需要一张首行为表头的表格）",
        )
    return _apply_requirements(project_id, rows, _mode(mode))


@router.post(
    "/projects/{project_id}/requirements/import/json",
    response_model=ImportResult,
    summary="粘贴大模型输出（JSON）导入需求",
)
def import_requirements_json(project_id: int, body: RequirementImportJson) -> ImportResult:
    _ensure_project(project_id)
    try:
        rows = extract_json_requirements(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not rows:
        raise HTTPException(status_code=400, detail="JSON 里没有可导入的需求")
    return _apply_requirements(project_id, rows, _mode(body.mode))


@router.post(
    "/projects/{project_id}/cases/import/xlsx",
    response_model=ImportResult,
    summary="从 Excel 导入测试用例（关联需求必须存在）",
)
async def import_cases_xlsx(
    project_id: int,
    file: UploadFile = File(..., description="用例清单 .xlsx"),
) -> ImportResult:
    _ensure_project(project_id)
    content = await _read_upload(file)
    try:
        rows = parse_cases_xlsx(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析 Excel 失败：{exc}") from exc
    if not rows:
        raise HTTPException(status_code=400, detail="表格里没有可导入的行（第一行应为表头）")
    return _apply_cases(project_id, rows)


@router.get(
    "/projects/{project_id}/requirements/export",
    summary="导出可编辑需求清单（xlsx）",
)
def export_requirements(
    project_id: int,
    fmt: Annotated[str, Query(alias="format", description="只支持 xlsx")] = "xlsx",
) -> Response:
    _ensure_project(project_id)
    if fmt.lower() != "xlsx":
        raise HTTPException(status_code=400, detail="需求清单只支持 xlsx 导出")
    content = build_requirements_workbook(req_service.get_requirements(project_id))
    filename = f"ratgp-requirements-project{project_id}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/projects/{project_id}/cases/export",
    summary="导出可编辑用例清单（xlsx）",
)
def export_cases(
    project_id: int,
    fmt: Annotated[str, Query(alias="format", description="只支持 xlsx")] = "xlsx",
) -> Response:
    _ensure_project(project_id)
    if fmt.lower() != "xlsx":
        raise HTTPException(status_code=400, detail="用例清单只支持 xlsx 导出")
    content = build_cases_workbook(repository.list_cases(project_id))
    filename = f"ratgp-cases-project{project_id}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
