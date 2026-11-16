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


# ---------- P3：需求 ----------

class SourceLocation(BaseModel):
    para_no: int | None = None
    raw: str | None = None
    ratio: float | None = None


class RequirementOut(BaseModel):
    req_id: str
    project_id: int
    title: str
    description: str
    req_type: str
    status: str
    acceptance: list[str] = Field(default_factory=list)
    source_location: SourceLocation | None = None
    is_ambiguous: bool = False


class RequirementListOut(BaseModel):
    items: list[RequirementOut]
    total: int
    confirmed: int
    ambiguous: int


class ExtractResult(BaseModel):
    document: DocumentMeta
    created: int
    skipped: int
    ambiguous: int
    replaced: bool
    elapsed_ms: int
    items: list[RequirementOut]


class RequirementStatusUpdate(BaseModel):
    status: str = Field(description="未审核 / 已确认 / 已驳回")


# ---------- P4：质量 ----------

class QualityIssue(BaseModel):
    issue_id: str
    kind: str = Field(description="ambiguous / conflict / missing_acceptance")
    severity: str = Field(description="warn / danger")
    title: str
    detail: str
    req_ids: list[str] = Field(default_factory=list)
    words: list[str] = Field(default_factory=list)


class QualitySummary(BaseModel):
    items: list[QualityIssue]
    total: int
    by_kind: dict[str, int] = Field(default_factory=dict)


# ---------- P5：测试用例 ----------

class TestCaseOut(BaseModel):
    tc_id: int
    req_id: str | None = None
    title: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_result: str
    test_type: str
    status: str


class CaseListOut(BaseModel):
    items: list[TestCaseOut]
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)


class CaseGenerateRequest(BaseModel):
    req_ids: list[str] | None = Field(None, description="不传则用全部已确认需求")
    replace: bool = Field(True, description="true=先清空这些需求的旧用例")


class CaseGenerateResult(BaseModel):
    created: int
    skipped: int
    by_type: dict[str, int] = Field(default_factory=dict)
    elapsed_ms: int
    req_ids: list[str] = Field(default_factory=list)
    items: list[TestCaseOut]


class CaseStatusUpdate(BaseModel):
    status: str = Field(description="已生成 / 已审核 / 已驳回")
