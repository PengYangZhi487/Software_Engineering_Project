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
    priority: str = "中"
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


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="需求标题")
    description: str = Field(min_length=1, description="需求描述")
    req_type: str = Field("functional", description="functional / non_functional")
    priority: str = Field("中", description="高 / 中 / 低")
    acceptance: list[str] = Field(default_factory=list, description="验收条件")


class RequirementUpdate(BaseModel):
    """全字段可选：只传要改的字段。"""

    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    req_type: str | None = None
    priority: str | None = None
    acceptance: list[str] | None = None
    status: str | None = None


# ---------- P4：质量 ----------

class QualityIssue(BaseModel):
    issue_id: str
    fingerprint: str = ""
    kind: str = Field(description="ambiguous / conflict / missing_acceptance")
    severity: str = Field(description="warn / danger")
    title: str
    detail: str
    req_ids: list[str] = Field(default_factory=list)
    words: list[str] = Field(default_factory=list)
    decision: str = Field("open", description="open / confirmed / ignored")


class QualitySummary(BaseModel):
    items: list[QualityIssue]
    total: int
    open: int = 0
    decided: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)


class QualityDecisionUpdate(BaseModel):
    decision: str = Field(description="open / confirmed / ignored")
    note: str | None = None


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
    status: str = Field(description="已生成 / 已审核 / 已驳回 / 已执行")


class CaseUpdate(BaseModel):
    """全字段可选：只传要改的字段。"""

    title: str | None = Field(None, min_length=1)
    preconditions: list[str] | None = None
    steps: list[str] | None = None
    expected_result: str | None = None
    test_type: str | None = None
    status: str | None = None


# ---------- P6：追踪 ----------

class TraceRequirement(BaseModel):
    req_id: str
    title: str
    status: str
    case_ids: list[int] = Field(default_factory=list)
    reviewed: int = 0
    covered: bool = False


class TraceCase(BaseModel):
    tc_id: int
    title: str
    test_type: str
    status: str
    req_id: str | None = None


class TraceSummary(BaseModel):
    confirmed: int = Field(description="分母：已确认需求数")
    covered: int = Field(description="分子：至少关联一条已审核用例的已确认需求数")
    coverage_pct: int
    linked_any: int = Field(0, description="至少关联一条用例（不论状态）的已确认需求数")
    cases: int = 0
    reviewed_cases: int = 0
    uncovered: int = 0


class TraceOut(BaseModel):
    summary: TraceSummary
    requirements: list[TraceRequirement]
    cases: list[TraceCase]


class CoverageOut(BaseModel):
    confirmed: int
    covered: int
    coverage_pct: int
    sql_covered: int
    consistent: bool


# ---------- P7：版本比对 ----------

class DiffCase(BaseModel):
    tc_id: int
    title: str
    req_id: str | None = None
    status: str
    test_type: str


class DiffChange(BaseModel):
    change_id: str
    kind: str = Field(description="changed / added / removed")
    base_para: int | None = None
    target_para: int | None = None
    base_text: str = ""
    target_text: str = ""
    removed_numbers: list[str] = Field(default_factory=list)
    added_numbers: list[str] = Field(default_factory=list)
    req_ids: list[str] = Field(default_factory=list)
    cases: list[DiffCase] = Field(default_factory=list)


class DiffSummary(BaseModel):
    added: int = 0
    removed: int = 0
    changed: int = 0
    affected_requirements: int = 0
    affected_cases: int = 0


class DiffOut(BaseModel):
    base: DocumentMeta
    target: DocumentMeta
    summary: DiffSummary
    changes: list[DiffChange]


# ---------- P8：报告 ----------

class ReportProject(BaseModel):
    project_id: int
    project_name: str
    description: str | None = None


class ReportCounts(BaseModel):
    requirements: int = 0
    confirmed: int = 0
    rejected: int = 0
    pending: int = 0
    issues: int = 0
    ambiguous: int = 0
    conflict: int = 0
    missing_acceptance: int = 0
    cases: int = 0
    case_generated: int = 0
    case_reviewed: int = 0
    case_rejected: int = 0
    covered_requirements: int = 0
    uncovered: int = 0
    coverage_pct: int = 0


class ReportOut(BaseModel):
    project: ReportProject
    documents: list[DocumentMeta]
    counts: ReportCounts
    generated_at: str


# ---------- 执行记录（生成 ≠ 执行 ≠ 通过） ----------

class ExecutionCreate(BaseModel):
    tc_id: int = Field(description="关联的用例编号")
    result: str = Field(description="pass / fail / blocked")
    actual_result: str | None = Field(None, description="实际结果")
    comments: str | None = Field(None, description="测试 comments")
    tester: str | None = Field(None, description="执行人")
    signature: str | None = Field(None, description="测试者签名")
    environment: str | None = Field(None, description="执行环境，如 Windows 11 / 浏览器版本")


class ExecutionOut(BaseModel):
    exec_id: int
    project_id: int
    tc_id: int
    result: str
    actual_result: str | None = None
    comments: str | None = None
    tester: str | None = None
    signature: str | None = None
    environment: str | None = None
    executed_at: str | None = None


class ExecutionListOut(BaseModel):
    items: list[ExecutionOut]
    total: int


class CaseBatchUpdate(BaseModel):
    tc_ids: list[int] = Field(min_length=1, description="要批量更新的用例编号")
    status: str = Field(description="已生成 / 已审核 / 已驳回 / 已执行")


# ---------- 全局搜索 ----------

class SearchOut(BaseModel):
    query: str
    requirements: list[RequirementOut] = Field(default_factory=list)
    cases: list[TestCaseOut] = Field(default_factory=list)
    quality: list[QualityIssue] = Field(default_factory=list)
    total: int = 0


# ---------- 导入导出（Excel 当编辑器） ----------

class ImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class RequirementImportJson(BaseModel):
    mode: str = Field("append", description="append 追加 / replace 先清空再导入")
    text: str = Field(description="粘贴的 JSON 文本，宽容纳 ```json 代码块包裹")
