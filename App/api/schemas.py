"""请求 / 响应模型。字段名与前端 mock 结构保持一致，P2 只做后端，前端照旧可先用 mock。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Paragraph(BaseModel):
    para_no: int
    text: str
    style: str = "Normal"
    is_heading: bool = False


class DocumentMeta(BaseModel):
    doc_id: int
    project_id: int
    filename: str
    version: str
    upload_time: str | None = None
    paragraphs: int = 0
    chars: int = 0
    file_path: str | None = None


class DocumentUploadResponse(BaseModel):
    document: DocumentMeta
    paragraphs: list[Paragraph]


class DocumentListResponse(BaseModel):
    items: list[DocumentMeta]
    total: int


class ProjectOut(BaseModel):
    project_id: int
    project_name: str
    description: str | None = None
    req_count: int = Field(0, description="该项目下的需求条数")


class HealthOut(BaseModel):
    status: str
    db: str
    projects: int | None = None
    version: str
