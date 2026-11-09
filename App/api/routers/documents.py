"""文档上传与解析。

POST /api/projects/{project_id}/documents   multipart: file + version
GET  /api/projects/{project_id}/documents
GET  /api/documents/{doc_id}
GET  /api/documents/{doc_id}/paragraphs

设计约束：
- 上传先落盘到 App/data/uploads，再解析、再入库；任何一步失败都会清理临时文件。
- 解析复用 App/services/doc_service.py，不在这里重写 docx/txt 的细节。
- 文件大小、扩展名、项目存在性都在协议层拦住，解析异常统一转 400。
"""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from App.api import repository
from App.api.config import ALLOWED_EXTS, MAX_UPLOAD_BYTES, UPLOAD_DIR
from App.api.schemas import DocumentListResponse, DocumentMeta, DocumentUploadResponse, Paragraph
from App.services.doc_service import parse_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])

_CHUNK = 1024 * 1024


def _to_paragraphs(para_index: list[dict]) -> list[Paragraph]:
    out: list[Paragraph] = []
    for p in para_index:
        style = p.get("style") or "Normal"
        out.append(
            Paragraph(
                para_no=int(p.get("para_no", 0)),
                text=p.get("raw") or "",
                style=style,
                is_heading=style.startswith("Heading"),
            )
        )
    return out


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
    summary="上传需求文档并解析段落",
)
async def upload_document(
    project_id: int,
    file: UploadFile = File(..., description="DOCX 或 TXT"),
    version: str = Form("V1.0", description="文档版本号，如 V1.0"),
) -> DocumentUploadResponse:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    original = Path(file.filename or "").name.strip()
    if not original:
        raise HTTPException(status_code=400, detail="缺少文件名")

    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型 {ext or '(无扩展名)'}，仅支持 {sorted(ALLOWED_EXTS)}",
        )

    clean_version = (version or "").strip() or "V1.0"
    if len(clean_version) > 20:
        raise HTTPException(status_code=400, detail="版本号过长（最多 20 个字符）")

    dest = UPLOAD_DIR / f"{uuid4().hex}{ext}"
    size = 0
    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过 {MAX_UPLOAD_BYTES // (1024 * 1024)} MB 上限",
                    )
                fh.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception as exc:  # 磁盘写入失败
        dest.unlink(missing_ok=True)
        logger.exception("保存上传文件失败")
        raise HTTPException(status_code=500, detail=f"保存文件失败：{exc}") from exc
    finally:
        await file.close()

    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="文件为空")

    try:
        text, para_index = parse_document(str(dest))
    except Exception as exc:
        dest.unlink(missing_ok=True)
        logger.warning("解析失败 %s: %s", original, exc)
        raise HTTPException(status_code=400, detail=f"解析失败：{exc}") from exc

    if not text.strip():
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="文档里没有可解析的文本（可能是扫描件或空文档）")

    try:
        meta = repository.insert_document(
            project_id=project_id,
            filename=original,
            version=clean_version,
            content_text=text,
            para_index=para_index,
            file_path=str(dest),
        )
    except Exception as exc:
        dest.unlink(missing_ok=True)
        logger.exception("入库失败")
        raise HTTPException(status_code=500, detail=f"入库失败：{exc}") from exc

    logger.info(
        "文档已入库 doc_id=%s project=%s file=%s 段落=%d 字符=%d",
        meta.doc_id, project_id, original, len(para_index), len(text),
    )
    return DocumentUploadResponse(document=meta, paragraphs=_to_paragraphs(para_index))


@router.get(
    "/projects/{project_id}/documents",
    response_model=DocumentListResponse,
    summary="某项目下的文档列表",
)
def list_documents(project_id: int) -> DocumentListResponse:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    items = repository.list_documents(project_id)
    return DocumentListResponse(items=items, total=len(items))


@router.get("/documents/{doc_id}", response_model=DocumentMeta, summary="文档元信息")
def get_document(doc_id: int) -> DocumentMeta:
    meta = repository.get_document(doc_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
    return meta


@router.get(
    "/documents/{doc_id}/paragraphs",
    response_model=list[Paragraph],
    summary="文档段落（含标题标记）",
)
def get_paragraphs(doc_id: int) -> list[Paragraph]:
    paragraphs = repository.get_paragraphs(doc_id)
    if paragraphs is None:
        raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
    return paragraphs
