"""接口冒烟测试：不依赖 httpx / TestClient，直接调用路由函数。

运行：
    cd Software_Engineering_Project
    venv\\Scripts\\python.exe -m unittest discover -s App/api/tests -v
"""
from __future__ import annotations

import asyncio
import inspect
import io
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# 允许指定临时目录（某些沙箱环境写不了系统 TEMP）
TMP = Path(os.environ.get("RATGP_TEST_TMP") or tempfile.mkdtemp(prefix="ratgp-api-test-"))
TMP.mkdir(parents=True, exist_ok=True)

# 必须在 import App.* 之前改掉数据库/上传目录，避免污染真实库
os.environ["RATGP_DB"] = str(TMP / "test.db")
os.environ["RATGP_UPLOAD_DIR"] = str(TMP / "uploads")
os.environ["RATGP_DATA_DIR"] = str(TMP)

from fastapi import HTTPException  # noqa: E402
from starlette.datastructures import UploadFile  # noqa: E402

from App.api import repository  # noqa: E402
from App.api.main import app  # noqa: E402
from App.api.routers.cases import (  # noqa: E402
    batch_update_cases,
    generate_cases as api_generate_cases,
    list_cases as api_list_cases,
    update_case,
)
from App.api.routers.executions import create_execution, list_executions  # noqa: E402
from App.api.routers.search import search as api_search  # noqa: E402
from App.api.routers.documents import upload_document  # noqa: E402
from App.api.routers.diff import document_diff  # noqa: E402
from App.api.routers.quality import decide_issue, list_issues  # noqa: E402
from App.api.routers.report import export_report, get_report  # noqa: E402
from App.api.routers.trace import get_coverage, get_trace  # noqa: E402
from App.api.routers.requirements import (  # noqa: E402
    create_requirement as api_create_requirement,
    extract_requirements,
    list_requirements,
    update_requirement,
)
from App.api.schemas import (  # noqa: E402
    CaseBatchUpdate,
    CaseGenerateRequest,
    CaseStatusUpdate,
    CaseUpdate,
    ExecutionCreate,
    QualityDecisionUpdate,
    RequirementCreate,
    RequirementStatusUpdate,
    RequirementUpdate,
)
from App.dao.db import get_connection, init_db  # noqa: E402
from App.services import case_service, llm_service, req_service  # noqa: E402
from App.services.doc_service import parse_document  # noqa: E402
from App.services.diff_service import diff_paragraphs  # noqa: E402
from App.services.quality_scan import scan_requirements  # noqa: E402

DOCX = ROOT / "tests" / "datasets" / "course_selection_v1.docx"
PROJECT_ID: int = 0


def setUpModule() -> None:
    global PROJECT_ID
    init_db()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Document")
        conn.execute("DELETE FROM Project")
        cur = conn.execute(
            "INSERT INTO Project (project_name, description) VALUES (?, ?)",
            ("测试项目", "P2 API 冒烟"),
        )
        PROJECT_ID = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()


def _upload(data: bytes, filename: str, version: str = "V1.0", project_id: int | None = None):
    up = UploadFile(filename=filename, file=io.BytesIO(data))
    return asyncio.run(upload_document(project_id or PROJECT_ID, up, version))


class ParseTests(unittest.TestCase):
    def test_docx_paragraphs_and_styles(self) -> None:
        self.assertTrue(DOCX.exists(), f"测试数据集缺失：{DOCX}")
        text, paras = parse_document(str(DOCX))
        self.assertEqual(len(paras), 52)
        self.assertGreater(len(text), 500)
        self.assertTrue(all("raw" in p for p in paras))
        headings = [p for p in paras if p["style"].startswith("Heading")]
        self.assertGreaterEqual(len(headings), 20, "标题样式应当被保留")

    def test_unknown_extension_rejected(self) -> None:
        bad = TMP / "a.pdf"
        bad.write_bytes(b"%PDF-1.4")
        with self.assertRaises(ValueError):
            parse_document(str(bad))

    def test_docx_table_rows_are_parsed(self) -> None:
        """表格里的需求不能丢：一行转一段，有表头时带列名。"""
        from docx import Document as Docx

        path = TMP / "with_table.docx"
        d = Docx()
        d.add_heading("校园选课系统需求", level=1)
        d.add_paragraph("需求如下：")
        t = d.add_table(rows=3, cols=3)
        for i, h in enumerate(["编号", "需求名称", "描述"]):
            t.rows[0].cells[i].text = h
        t.rows[1].cells[0].text = "REQ-001"
        t.rows[1].cells[1].text = "课程容量"
        t.rows[1].cells[2].text = "每门课程最多容纳50人。"
        t.rows[2].cells[0].text = "REQ-002"
        t.rows[2].cells[1].text = "退课截止"
        t.rows[2].cells[2].text = "第2周周五18:00后不可退课。"
        d.add_paragraph("以上为全部需求。")
        d.save(path)

        text, paras = parse_document(str(path))

        self.assertIn("REQ-001", text)
        self.assertIn("每门课程最多容纳50人", text)
        self.assertIn("第2周周五18:00后不可退课", text)
        self.assertIn("以上为全部需求", text, "表格之后的段落不能丢")
        self.assertIn("编号：REQ-001", text, "有表头时应带列名")
        self.assertEqual(
            [p["style"] for p in paras],
            ["Heading 1", "Normal", "Table", "Table", "Normal"],
        )
        self.assertEqual([p["para_no"] for p in paras], [0, 1, 2, 3, 4],
                         "段落与表格行应共用连续坐标")


class ApiTests(unittest.TestCase):
    def test_routes_registered(self) -> None:
        # FastAPI 较新版本把 include_router 的结果延迟展开，直接看 app.routes 拿不到；
        # 用 OpenAPI 文档验证更稳。
        paths = set(app.openapi().get("paths", {}))
        self.assertIn("/api/health", paths)
        self.assertIn("/api/projects", paths)
        self.assertIn("/api/projects/{project_id}/documents", paths)
        self.assertIn("/api/documents/{doc_id}/paragraphs", paths)
        self.assertIn("/api/projects/{project_id}/requirements", paths)
        self.assertIn("/api/projects/{project_id}/requirements/extract", paths)
        self.assertIn("/api/projects/{project_id}/requirements/{req_id}", paths)
        self.assertIn("/api/projects/{project_id}/quality/issues", paths)
        self.assertIn("/api/projects/{project_id}/cases", paths)
        self.assertIn("/api/projects/{project_id}/cases/generate", paths)
        self.assertIn("/api/projects/{project_id}/cases/{tc_id}", paths)
        self.assertIn("/api/projects/{project_id}/trace", paths)
        self.assertIn("/api/projects/{project_id}/trace/coverage", paths)
        self.assertIn("/api/projects/{project_id}/document-diff", paths)
        self.assertIn("/api/projects/{project_id}/report", paths)
        self.assertIn("/api/projects/{project_id}/report/export", paths)

    def test_upload_then_read(self) -> None:
        data = DOCX.read_bytes()
        resp = _upload(data, "course_selection_v1.docx", "V2.0")

        self.assertGreater(resp.document.doc_id, 0)
        self.assertEqual(resp.document.version, "V2.0")
        self.assertEqual(resp.document.paragraphs, 52)
        self.assertGreater(resp.document.chars, 500)
        self.assertEqual(len(resp.paragraphs), 52)
        self.assertTrue(any(p.is_heading for p in resp.paragraphs))

        meta = repository.get_document(resp.document.doc_id)
        self.assertIsNotNone(meta)
        self.assertEqual(meta.filename, "course_selection_v1.docx")

        paras = repository.get_paragraphs(resp.document.doc_id)
        self.assertEqual(len(paras), 52)

        docs = repository.list_documents(PROJECT_ID)
        self.assertTrue(any(d.doc_id == resp.document.doc_id for d in docs))

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT file_path FROM Document WHERE doc_id = ?", (resp.document.doc_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertTrue(Path(row["file_path"]).exists(), "原始文件应落盘保留")
        self.assertNotIn("file_path", resp.document.model_dump(), "元信息不应暴露服务器路径")

    def test_upload_rejects_wrong_type(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            _upload(b"%PDF-1.4", "spec.pdf")
        self.assertEqual(ctx.exception.status_code, 415)

    def test_upload_rejects_missing_project(self) -> None:
        up = UploadFile(filename="a.txt", file=io.BytesIO(b"hello"))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(upload_document(99999, up, "V1.0"))
        self.assertEqual(ctx.exception.status_code, 404)

    def test_upload_rejects_empty_text(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            _upload("   \n\n  ".encode("utf-8"), "empty.txt")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_upload_rejects_zip_bomb(self) -> None:
        """10 MB 的 docx 可能解压出几个 GB，解析前必须拒绝。"""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("word/document.xml", "<x>" + "a" * (2 * 1024 * 1024) + "</x>")

        with self.assertRaises(HTTPException) as ctx:
            _upload(buf.getvalue(), "bomb.docx")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("体积", ctx.exception.detail)


class RequirementFlowTests(unittest.TestCase):
    """抽取 → 确认 → 驳回，全程用假的 LLM 结果，不耗 API 额度。"""

    def test_extract_confirm_reject(self) -> None:
        from unittest.mock import patch

        if not repository.list_documents(PROJECT_ID):
            _upload(DOCX.read_bytes(), "course_selection_v1.docx", "V1.0")

        fake = llm_service.RequirementList(
            requirements=[
                llm_service.Requirement(
                    req_id="X-1",
                    title="课程容量",
                    description="课程默认容量 50 人，达到上限后拒绝新选课。",
                    req_type="functional",
                    acceptance_criteria=["已选 50 人时拒绝第 51 人"],
                ),
                llm_service.Requirement(
                    req_id="X-2",
                    title="系统响应快速",
                    description="系统响应快速，查询时无明显等待。",
                    req_type="non_functional",
                    acceptance_criteria=["查询无卡顿"],
                ),
            ]
        )

        with patch.object(llm_service, "extract_requirements", return_value=fake):
            result = extract_requirements(PROJECT_ID, None, True, "test-key")

        # 编号由程序生成，不采信模型给的 X-1 / X-2
        self.assertEqual([item.req_id for item in result.items], ["CR-001", "CR-002"])
        self.assertEqual(result.created, 2)
        self.assertEqual(result.replaced, True)
        self.assertTrue(result.items[1].is_ambiguous, "「快速」「明显」应被标为模糊")
        self.assertEqual(result.items[0].status, "未审核")

        confirmed = update_requirement(
            PROJECT_ID, "CR-001", RequirementStatusUpdate(status="已确认")
        )
        self.assertEqual(confirmed.status, "已确认")

        rejected = update_requirement(
            PROJECT_ID, "CR-002", RequirementStatusUpdate(status="已驳回")
        )
        self.assertEqual(rejected.status, "已驳回")

        listing = list_requirements(PROJECT_ID, None)
        self.assertEqual(listing.total, 2)
        self.assertEqual(listing.confirmed, 1)
        self.assertEqual(listing.ambiguous, 1)

        with self.assertRaises(HTTPException) as missing:
            update_requirement(PROJECT_ID, "CR-999", RequirementStatusUpdate(status="已确认"))
        self.assertEqual(missing.exception.status_code, 404)

        with self.assertRaises(HTTPException) as illegal:
            update_requirement(PROJECT_ID, "CR-001", RequirementStatusUpdate(status="随便"))
        self.assertEqual(illegal.exception.status_code, 422)

    def test_two_projects_can_reuse_req_id(self) -> None:
        """C 方案的核心验收：两个项目各自从 CR-001 开始，互不冲突。"""
        from unittest.mock import patch

        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO Project (project_name) VALUES ('第二个项目')")
            p2 = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()

        _upload(DOCX.read_bytes(), "course_v2.docx", "V1.0", p2)

        fake = llm_service.RequirementList(
            requirements=[
                llm_service.Requirement(
                    req_id="X-1",
                    title="课程容量",
                    description="课程默认容量 50 人。",
                    req_type="functional",
                    acceptance_criteria=["50 人后拒绝"],
                )
            ]
        )
        with patch.object(llm_service, "extract_requirements", return_value=fake):
            result = extract_requirements(p2, None, True, "test-key")

        self.assertEqual(result.created, 1)
        self.assertEqual([item.req_id for item in result.items], ["CR-001"])

        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT project_id, req_id FROM Requirement WHERE req_id = 'CR-001' ORDER BY project_id"
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual([int(r["project_id"]) for r in rows], [PROJECT_ID, p2],
                         "同一个 CR-001 应能在两个项目下并存")

    def test_extract_requires_document(self) -> None:
        # 新项目没有任何文档，抽取应报 400 而不是 500
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO Project (project_name) VALUES ('空项目')")
            empty_project = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(HTTPException) as ctx:
            extract_requirements(empty_project, None, True, "test-key")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_extract_rejects_foreign_document(self) -> None:
        """A 项目的接口不能拿 B 项目的 doc_id 抽取。"""
        conn = get_connection()
        try:
            cur = conn.execute("INSERT INTO Project (project_name) VALUES ('别的项目')")
            other = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()

        foreign = _upload(DOCX.read_bytes(), "other.docx", "V1.0", other)
        with self.assertRaises(HTTPException) as ctx:
            extract_requirements(PROJECT_ID, foreign.document.doc_id, True, "test-key")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("不属于", ctx.exception.detail)

    def test_manual_create_and_edit(self) -> None:
        created = api_create_requirement(
            PROJECT_ID,
            RequirementCreate(
                title="退课申请审批",
                description="学生退课后需教师审批，审批通过才释放名额。",
                req_type="functional",
                priority="高",
                acceptance=["审批通过后名额释放", "审批拒绝后保留名额"],
            ),
        )
        self.assertEqual(created.req_id, "CR-003", "编号应接着项目最大号续")
        self.assertEqual(created.priority, "高")
        self.assertEqual(created.status, "未审核")
        self.assertIsNone(created.source_location, "手动建的需求没有来源段落")
        self.assertFalse(created.is_ambiguous)

        edited = update_requirement(
            PROJECT_ID,
            created.req_id,
            RequirementUpdate(title="退课申请要快速审批", description="审批尽快完成。"),
        )
        self.assertEqual(edited.title, "退课申请要快速审批")
        self.assertTrue(edited.is_ambiguous, "改后含「快速 / 尽快」应重新标记")

        with self.assertRaises(HTTPException) as bad:
            update_requirement(
                PROJECT_ID, created.req_id, RequirementUpdate(priority="紧急")
            )
        self.assertEqual(bad.exception.status_code, 422)

    def test_quality_decision_persists(self) -> None:
        issues = list_issues(PROJECT_ID)
        self.assertGreater(issues.total, 0, "CR-002 含模糊词，应至少有一条问题")
        target = next(i for i in issues.items if i.kind == "ambiguous")
        self.assertEqual(target.decision, "open")

        decide_issue(
            PROJECT_ID, target.fingerprint, QualityDecisionUpdate(decision="ignored")
        )
        again = list_issues(PROJECT_ID)
        hit = next(i for i in again.items if i.fingerprint == target.fingerprint)
        self.assertEqual(hit.decision, "ignored")
        self.assertEqual(again.decided, 1)

        decide_issue(
            PROJECT_ID, target.fingerprint, QualityDecisionUpdate(decision="open")
        )
        restored = list_issues(PROJECT_ID)
        self.assertEqual(
            next(i for i in restored.items if i.fingerprint == target.fingerprint).decision,
            "open",
        )

    def test_requires_api_key(self) -> None:
        """没有请求头、也没有环境变量时，两个 LLM 接口都应 401。"""
        from unittest.mock import patch

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            with self.assertRaises(HTTPException) as extract_ctx:
                extract_requirements(PROJECT_ID, None, True, None)
            self.assertEqual(extract_ctx.exception.status_code, 401)
            self.assertIn("API Key", extract_ctx.exception.detail)

            with self.assertRaises(HTTPException) as case_ctx:
                api_generate_cases(PROJECT_ID, CaseGenerateRequest(), None)
            self.assertEqual(case_ctx.exception.status_code, 401)


class QualityScanTests(unittest.TestCase):
    """规则引擎是纯函数，直接喂数据断言，不依赖数据库。"""

    def test_scan_detects_expected_kinds(self) -> None:
        rows = [
            {"req_id": "R1", "title": "选课门数", "description": "每学期最多选 6 门课程。", "acceptance": ["满 6 门拒绝"]},
            {"req_id": "R2", "title": "允许选 8 门", "description": "允许学生每学期选 8 门课程。", "acceptance": []},
            {"req_id": "R3", "title": "成绩发布后不可改", "description": "成绩发布后不可修改。", "acceptance": ["拒绝修改"]},
            {"req_id": "R4", "title": "成绩 7 天内可改", "description": "教师可在成绩发布后 7 天内修改成绩。", "acceptance": ["允许修改"]},
            {"req_id": "R5", "title": "系统响应快速", "description": "查询时无明显等待。", "acceptance": ["响应可接受"]},
        ]
        issues = scan_requirements(rows)
        kinds = {issue["kind"] for issue in issues}

        self.assertIn("ambiguous", kinds)
        self.assertIn("conflict", kinds)
        self.assertIn("missing_acceptance", kinds)

        titles = [issue["title"] for issue in issues if issue["kind"] == "conflict"]
        self.assertTrue(any("门数" in t for t in titles), titles)
        self.assertTrue(any("成绩" in t for t in titles), titles)

        # 同一份数据重复扫描，结果必须一致（可复算）
        again = scan_requirements(rows)
        self.assertEqual([i["issue_id"] for i in issues], [i["issue_id"] for i in again])
        self.assertEqual([i["title"] for i in issues], [i["title"] for i in again])


class CaseFlowTests(unittest.TestCase):
    """用例生成 → 审核 → 驳回，全程用假的 LLM 结果。"""

    def setUp(self) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM RequirementTestLink")
            conn.execute("DELETE FROM TestCase")
            conn.execute(
                "DELETE FROM Requirement WHERE project_id = ? AND req_id = 'CR-901'",
                (PROJECT_ID,),
            )
            conn.execute(
                """
                INSERT INTO Requirement
                    (req_id, project_id, title, description, acceptance, req_type, status, is_ambiguous)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "CR-901",
                    PROJECT_ID,
                    "课程容量",
                    "课程默认容量 50 人，达到上限后拒绝新选课。",
                    json.dumps(["已选 49 人时允许", "已选 50 人时拒绝"], ensure_ascii=False),
                    "functional",
                    "已确认",
                    0,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def test_generate_and_review(self) -> None:
        from unittest.mock import patch

        fake = case_service.GeneratedCaseList(
            cases=[
                case_service.GeneratedCase(
                    req_id="CR-901",
                    title="容量未满时选课成功",
                    preconditions=["课程已选 49 人"],
                    steps=["学生提交选课请求"],
                    expected_result="选课成功，人数变为 50",
                    test_type="normal",
                ),
                case_service.GeneratedCase(
                    req_id="CR-901",
                    title="第 51 人被拒绝",
                    preconditions=["课程已选 50 人"],
                    steps=["第 51 名学生提交选课"],
                    expected_result="拒绝并提示课程已满",
                    test_type="boundary",
                ),
                case_service.GeneratedCase(
                    req_id="CR-999",
                    title="引用了不存在的需求",
                    preconditions=[],
                    steps=["x"],
                    expected_result="y",
                    test_type="abnormal",
                ),
            ]
        )

        with patch.object(case_service, "generate_cases", return_value=fake):
            result = api_generate_cases(PROJECT_ID, CaseGenerateRequest(replace=True), "test-key")

        # CR-999 会因外键约束写不进去，计入 skipped
        self.assertEqual(result.created, 2)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.by_type, {"normal": 1, "boundary": 1})
        self.assertIn("CR-901", result.req_ids)

        listing = api_list_cases(PROJECT_ID)
        self.assertGreaterEqual(listing.total, 2)
        self.assertEqual(listing.by_status.get("已生成"), 2)
        case = listing.items[0]

        reviewed = update_case(PROJECT_ID, case.tc_id, CaseStatusUpdate(status="已审核"))
        self.assertEqual(reviewed.status, "已审核")

        rejected = update_case(PROJECT_ID, case.tc_id, CaseStatusUpdate(status="已驳回"))
        self.assertEqual(rejected.status, "已驳回")

        with self.assertRaises(HTTPException) as missing:
            update_case(PROJECT_ID, 999999, CaseStatusUpdate(status="已审核"))
        self.assertEqual(missing.exception.status_code, 404)

        with self.assertRaises(HTTPException) as illegal:
            update_case(PROJECT_ID, case.tc_id, CaseStatusUpdate(status="随便"))
        self.assertEqual(illegal.exception.status_code, 422)

        edited = update_case(
            PROJECT_ID,
            case.tc_id,
            CaseUpdate(
                title="容量未满时选课成功（修订）",
                steps=["学生提交选课请求", "系统校验名额"],
                test_type="normal",
                status="已执行",
            ),
        )
        self.assertEqual(edited.title, "容量未满时选课成功（修订）")
        self.assertEqual(edited.steps, ["学生提交选课请求", "系统校验名额"])
        self.assertEqual(edited.status, "已执行")

        with self.assertRaises(HTTPException) as bad_type:
            update_case(PROJECT_ID, case.tc_id, CaseUpdate(test_type="smoke"))
        self.assertEqual(bad_type.exception.status_code, 422)

    def test_generate_requires_confirmed(self) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE Requirement SET status = '未审核' WHERE project_id = ?", (PROJECT_ID,))
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(HTTPException) as ctx:
            api_generate_cases(PROJECT_ID, CaseGenerateRequest(), "test-key")
        self.assertEqual(ctx.exception.status_code, 400)


class TraceTests(unittest.TestCase):
    """矩阵 + 覆盖率：口径固定为「已确认需求 × 已审核用例」。"""

    def setUp(self) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE Requirement SET status = '未审核' WHERE project_id = ?", (PROJECT_ID,))
            conn.execute(
                "INSERT OR IGNORE INTO Requirement (req_id, project_id, title, description, acceptance, req_type, status, is_ambiguous) "
                "VALUES ('CR-901', ?, '课程容量', '达到 50 人后拒绝', '[]', 'functional', '已确认', 0)",
                (PROJECT_ID,),
            )
            conn.execute(
                "UPDATE Requirement SET status = '已确认' WHERE project_id = ? AND req_id = 'CR-901'",
                (PROJECT_ID,),
            )
            conn.execute("DELETE FROM RequirementTestLink")
            conn.execute("DELETE FROM TestCase")
            cur = conn.execute(
                "INSERT INTO TestCase "
                "(project_id, req_id, title, steps, expected_result, test_type, status) "
                "VALUES (?, 'CR-901', '容量边界', '[\"提交选课\"]', '拒绝', 'boundary', '已审核')",
                (PROJECT_ID,),
            )
            conn.execute(
                "INSERT INTO RequirementTestLink (project_id, req_id, tc_id, link_source) "
                "VALUES (?, 'CR-901', ?, 'AI')",
                (PROJECT_ID, cur.lastrowid),
            )
            conn.commit()
        finally:
            conn.close()

    def test_matrix_reflects_confirmed_and_reviewed(self) -> None:
        trace = get_trace(PROJECT_ID)
        self.assertEqual(trace.summary.confirmed, 1)
        self.assertEqual(trace.summary.covered, 1)
        self.assertEqual(trace.summary.coverage_pct, 100)

        row = next(r for r in trace.requirements if r.req_id == "CR-901")
        self.assertTrue(row.covered)
        self.assertEqual(len(row.case_ids), 1)

        cov = get_coverage(PROJECT_ID)
        self.assertTrue(cov.consistent, "矩阵口径与纯 SQL 复算必须一致")
        self.assertEqual(cov.covered, cov.sql_covered)
        self.assertEqual(cov.coverage_pct, 100)

    def test_rejecting_case_drops_coverage(self) -> None:
        trace = get_trace(PROJECT_ID)
        tc_id = trace.cases[0].tc_id

        update_case(PROJECT_ID, tc_id, CaseStatusUpdate(status="已驳回"))
        cov = get_coverage(PROJECT_ID)
        self.assertEqual(cov.covered, 0)
        self.assertEqual(cov.coverage_pct, 0)
        self.assertTrue(cov.consistent)

        update_case(PROJECT_ID, tc_id, CaseStatusUpdate(status="已审核"))
        self.assertEqual(get_coverage(PROJECT_ID).coverage_pct, 100)


class DiffTests(unittest.TestCase):
    """两版文档比对 + 受影响用例。"""

    def setUp(self) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM RequirementTestLink")
            conn.execute("DELETE FROM TestCase")
            conn.execute("DELETE FROM Requirement WHERE project_id = ?", (PROJECT_ID,))
            conn.execute("DELETE FROM Document")

            base_paras = [
                {"para_no": 0, "raw": "校园选课系统需求说明书", "style": "Heading 1"},
                {"para_no": 1, "raw": "课程容量 50 人，满员拒绝。", "style": "Normal"},
                {"para_no": 2, "raw": "退课截止第 2 周。", "style": "Normal"},
            ]
            target_paras = [
                {"para_no": 0, "raw": "校园选课系统需求说明书", "style": "Heading 1"},
                {"para_no": 1, "raw": "课程容量 60 人，满员拒绝。", "style": "Normal"},
                {"para_no": 2, "raw": "退课截止第 3 周。", "style": "Normal"},
            ]

            base_id = conn.execute(
                "INSERT INTO Document (project_id, filename, version, content_text, para_index) VALUES (?,?,?,?,?)",
                (PROJECT_ID, "v1.docx", "V1.0", "base", json.dumps(base_paras, ensure_ascii=False)),
            ).lastrowid
            conn.execute(
                "INSERT INTO Document (project_id, filename, version, content_text, para_index) VALUES (?,?,?,?,?)",
                (PROJECT_ID, "v2.docx", "V1.1", "target", json.dumps(target_paras, ensure_ascii=False)),
            )

            conn.execute(
                """
                INSERT INTO Requirement
                    (req_id, project_id, doc_id, title, description, acceptance, req_type, status, source_location, is_ambiguous)
                VALUES ('CR-950', ?, ?, '课程容量', '课程容量 50 人，满员拒绝。', '[]', 'functional', '已确认', ?, 0)
                """,
                (
                    PROJECT_ID,
                    base_id,
                    json.dumps(
                        {"para_no": 1, "raw": "课程容量 50 人，满员拒绝。", "ratio": 1.0},
                        ensure_ascii=False,
                    ),
                ),
            )
            case_id = conn.execute(
                "INSERT INTO TestCase "
                "(project_id, req_id, title, steps, expected_result, test_type, status) "
                "VALUES (?, 'CR-950', '容量边界', '[]', '拒绝', 'boundary', '已审核')",
                (PROJECT_ID,),
            ).lastrowid
            conn.execute(
                "INSERT INTO RequirementTestLink (project_id, req_id, tc_id, link_source) "
                "VALUES (?, 'CR-950', ?, 'AI')",
                (PROJECT_ID, case_id),
            )
            conn.commit()
        finally:
            conn.close()

    def test_unit_diff_kinds(self) -> None:
        base = [{"para_no": 1, "raw": "A"}, {"para_no": 2, "raw": "B"}, {"para_no": 3, "raw": "C"}]
        target = [{"para_no": 1, "raw": "A"}, {"para_no": 2, "raw": "B2"}]
        kinds = [c["kind"] for c in diff_paragraphs(base, target)]
        self.assertIn("changed", kinds)
        self.assertIn("removed", kinds)

        base2 = [{"para_no": 1, "raw": "A"}]
        target2 = [{"para_no": 1, "raw": "A"}, {"para_no": 2, "raw": "新段落"}]
        self.assertEqual([c["kind"] for c in diff_paragraphs(base2, target2)], ["added"])

    def test_endpoint_and_impact(self) -> None:
        out = document_diff(PROJECT_ID, None, None)

        self.assertEqual(out.summary.changed, 2)
        self.assertEqual(out.summary.affected_requirements, 1)
        self.assertEqual(out.summary.affected_cases, 1)

        with_req = [c for c in out.changes if c.req_ids]
        self.assertEqual(len(with_req), 1)
        change = with_req[0]
        self.assertIn("CR-950", change.req_ids)
        self.assertEqual(change.removed_numbers, ["50"])
        self.assertEqual(change.added_numbers, ["60"])
        self.assertEqual(change.cases[0].status, "已审核")


class A3TransactionTests(unittest.TestCase):
    """A3：抽取写入必须是「清空 + 插入」同一事务，失败整体回滚。"""

    def setUp(self) -> None:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO Project (project_name) VALUES ('A3 事务测试项目')"
            )
            self.pid = int(cur.lastrowid)
            conn.commit()
        finally:
            conn.close()

    def tearDown(self) -> None:
        """按外键顺序清掉本测试的项目，避免污染共享测试库。"""
        pid = getattr(self, "pid", None)
        if pid is None:
            return
        conn = get_connection()
        try:
            for table in (
                "ChangeLog", "RequirementTestLink", "TestCase", "QualityDecision",
            ):
                conn.execute(f"DELETE FROM {table} WHERE project_id = ?", (pid,))
            conn.execute("DELETE FROM Requirement WHERE project_id = ?", (pid,))
            conn.execute("DELETE FROM Document WHERE project_id = ?", (pid,))
            conn.execute("DELETE FROM Project WHERE project_id = ?", (pid,))
            conn.commit()
        finally:
            conn.close()

    def _count(self, table: str) -> int:
        conn = get_connection()
        try:
            return int(
                conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (self.pid,)
                ).fetchone()[0]
            )
        finally:
            conn.close()

    def _req_row(self, req_id: str):
        conn = get_connection()
        try:
            return conn.execute(
                "SELECT title, description FROM Requirement "
                "WHERE project_id = ? AND req_id = ?",
                (self.pid, req_id),
            ).fetchone()
        finally:
            conn.close()

    def test_failed_insert_rolls_back_clear(self) -> None:
        """一批里有一条写坏时整体回滚：旧需求不能先被清空，也不能只写半截。"""
        req_service.save_requirements(
            self.pid,
            None,
            [{"req_id": "CR-001", "title": "课程容量", "description": "课程默认容量 50 人。"}],
        )

        # 同一批里出现重复 req_id：第二条触发 UNIQUE(project_id, req_id)
        bad = [
            {"req_id": "CR-001", "title": "容量 60 人", "description": "容量改为 60 人。"},
            {"req_id": "CR-001", "title": "容量 70 人", "description": "容量改为 70 人。"},
        ]
        with self.assertRaises(sqlite3.IntegrityError):
            req_service.save_requirements(self.pid, None, bad, clear_first=True)

        self.assertEqual(self._count("Requirement"), 1, "回滚后旧需求应原样保留")
        row = self._req_row("CR-001")
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "课程容量", "旧数据不能被半截写入覆盖")

    def test_replace_clears_changelog_before_requirement(self) -> None:
        """清空顺序：先删 ChangeLog 等子表，再删 Requirement，否则外键会拦。"""
        req_service.save_requirements(
            self.pid,
            None,
            [{"req_id": "CR-001", "title": "课程容量", "description": "课程默认容量 50 人。"}],
        )
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO ChangeLog (project_id, req_id, version, change_type) "
                "VALUES (?, 'CR-001', 'V1.0', 'changed')",
                (self.pid,),
            )
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self._count("ChangeLog"), 1)

        stats = req_service.save_requirements(
            self.pid,
            None,
            [{"req_id": "CR-001", "title": "课程容量", "description": "课程默认容量 60 人。"}],
            clear_first=True,
        )
        self.assertEqual(stats["saved"], 1)
        self.assertEqual(self._count("ChangeLog"), 0, "旧 ChangeLog 必须一并清掉")

    def test_extract_replace_defaults_to_false(self) -> None:
        """接口层：不传 replace 时按追加处理，不能默认覆盖旧需求。"""
        default = inspect.signature(extract_requirements).parameters["replace"].default
        self.assertIs(getattr(default, "default", default), False)

    def test_extract_appends_when_replace_false(self) -> None:
        """显式 replace=false 时续号追加，已有需求不受影响。"""
        from unittest.mock import patch

        _upload(DOCX.read_bytes(), "a3.docx", "V1.0", self.pid)
        fake = llm_service.RequirementList(
            requirements=[
                llm_service.Requirement(
                    req_id="X-1",
                    title="课程容量",
                    description="课程默认容量 50 人。",
                    req_type="functional",
                    acceptance_criteria=["50 人后拒绝"],
                )
            ]
        )
        with patch.object(llm_service, "extract_requirements", return_value=fake):
            first = extract_requirements(self.pid, None, False, "test-key")
            second = extract_requirements(self.pid, None, False, "test-key")

        self.assertEqual([i.req_id for i in first.items], ["CR-001"])
        self.assertEqual([i.req_id for i in second.items], ["CR-001", "CR-002"])
        self.assertFalse(second.replaced)


class ReportTests(unittest.TestCase):
    """报告数字必须与各模块口径一致，导出的 CSV 必须能复现这些数字。"""

    def test_report_matches_modules(self) -> None:
        report = get_report(PROJECT_ID)
        trace = get_trace(PROJECT_ID)
        quality = list_issues(PROJECT_ID)

        self.assertEqual(report.counts.coverage_pct, trace.summary.coverage_pct)
        self.assertEqual(report.counts.covered_requirements, trace.summary.covered)
        self.assertEqual(report.counts.issues, quality.total)
        self.assertEqual(
            report.counts.requirements,
            len(req_service.get_requirements(PROJECT_ID)),
        )
        self.assertEqual(report.counts.cases, len(repository.list_cases(PROJECT_ID)))

    def test_csv_export(self) -> None:
        report = get_report(PROJECT_ID)
        response = export_report(PROJECT_ID, "csv")
        body = response.body.decode("utf-8")

        self.assertTrue(body.startswith("\ufeff"), "CSV 需要带 BOM，Excel 才不会乱码")
        self.assertIn("需求清单", body)
        self.assertIn("测试用例", body)
        self.assertIn(f"# 覆盖率(%),{report.counts.coverage_pct}", body)
        self.assertIn(f"# 需求总数,{report.counts.requirements}", body)

        with self.assertRaises(HTTPException) as ctx:
            export_report(PROJECT_ID, "pdf")
        self.assertEqual(ctx.exception.status_code, 400)

        xlsx = export_report(PROJECT_ID, "xlsx")
        self.assertIn("spreadsheetml", xlsx.media_type)


def _new_project(name: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO Project (project_name) VALUES (?)", (name,))
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def _drop_project(pid: int) -> None:
    if not pid:
        return
    conn = get_connection()
    try:
        for table in ("Execution", "ChangeLog", "RequirementTestLink", "TestCase", "QualityDecision"):
            conn.execute(f"DELETE FROM {table} WHERE project_id = ?", (pid,))
        conn.execute("DELETE FROM Requirement WHERE project_id = ?", (pid,))
        conn.execute("DELETE FROM Document WHERE project_id = ?", (pid,))
        conn.execute("DELETE FROM Project WHERE project_id = ?", (pid,))
        conn.commit()
    finally:
        conn.close()


def _seed_project(pid: int) -> dict:
    """给独立测试项目建一条需求 + 一条用例，返回用例。"""
    req_service.save_requirements(
        pid,
        None,
        [
            {
                "req_id": "CR-001",
                "title": "课程容量",
                "description": "课程默认容量 50 人，系统响应快速。",
                "acceptance_criteria": ["第 51 人拒绝"],
            }
        ],
    )
    return repository.insert_case(
        project_id=pid,
        req_id="CR-001",
        title="容量边界 50 人",
        preconditions=["课程已满 50 人"],
        steps=["学生选课"],
        expected_result="拒绝并提示容量已满",
        test_type="boundary",
    )


class ExecutionTests(unittest.TestCase):
    """执行记录：生成 ≠ 执行 ≠ 通过。"""

    def setUp(self) -> None:
        self.pid = _new_project("执行记录测试")
        self.case = _seed_project(self.pid)

    def tearDown(self) -> None:
        _drop_project(self.pid)

    def test_create_and_list(self) -> None:
        out = create_execution(
            self.pid,
            ExecutionCreate(
                tc_id=self.case["tc_id"],
                result="pass",
                actual_result="第 51 人被拒绝，提示容量已满",
                comments="边界值符合预期",
                tester="张三",
                signature="ZS",
                environment="Windows 11 / Chrome 141",
            ),
        )
        self.assertEqual(out.result, "pass")
        self.assertEqual(out.signature, "ZS")

        listing = list_executions(self.pid)
        self.assertEqual(listing.total, 1)
        self.assertEqual(listing.items[0].comments, "边界值符合预期")

        # 执行不改写用例审核状态（覆盖率口径依赖「已审核」）
        case = repository.get_case(self.case["tc_id"])
        self.assertEqual(case["status"], "已生成")

    def test_rejects_bad_result_and_foreign_case(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            create_execution(self.pid, ExecutionCreate(tc_id=self.case["tc_id"], result="ok"))
        self.assertEqual(ctx.exception.status_code, 422)

        other = _new_project("另一个项目")
        try:
            with self.assertRaises(HTTPException) as ctx2:
                create_execution(other, ExecutionCreate(tc_id=self.case["tc_id"], result="pass"))
            self.assertEqual(ctx2.exception.status_code, 404)
        finally:
            _drop_project(other)


class CaseBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pid = _new_project("批量审核测试")
        _seed_project(self.pid)

    def tearDown(self) -> None:
        _drop_project(self.pid)

    def test_batch_review_and_reject(self) -> None:
        tc_id = repository.list_cases(self.pid)[0]["tc_id"]
        out = batch_update_cases(self.pid, CaseBatchUpdate(tc_ids=[tc_id], status="已审核"))
        self.assertEqual(out["updated"], 1)
        self.assertEqual(repository.get_case(tc_id)["status"], "已审核")

        out2 = batch_update_cases(self.pid, CaseBatchUpdate(tc_ids=[tc_id], status="已驳回"))
        self.assertEqual(out2["updated"], 1)
        self.assertEqual(repository.get_case(tc_id)["status"], "已驳回")

    def test_rejects_illegal_status(self) -> None:
        tc_id = repository.list_cases(self.pid)[0]["tc_id"]
        with self.assertRaises(HTTPException) as ctx:
            batch_update_cases(self.pid, CaseBatchUpdate(tc_ids=[tc_id], status="通过"))
        self.assertEqual(ctx.exception.status_code, 422)


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pid = _new_project("搜索测试")
        _seed_project(self.pid)

    def tearDown(self) -> None:
        _drop_project(self.pid)

    def test_search_hits_requirements_cases_and_quality(self) -> None:
        res = api_search(self.pid, "容量")
        self.assertGreaterEqual(res.total, 1)
        self.assertEqual([r.req_id for r in res.requirements], ["CR-001"])
        self.assertEqual(res.cases[0].title, "容量边界 50 人")

        # 「快速」是模糊词：需求命中，质量扫描也应命中
        res2 = api_search(self.pid, "快速")
        self.assertTrue(res2.requirements)
        self.assertTrue(res2.quality)

    def test_search_requires_project(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            api_search(999999, "容量")
        self.assertEqual(ctx.exception.status_code, 404)


class XlsxExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pid = _new_project("Excel 导出测试")
        self.case = _seed_project(self.pid)
        create_execution(
            self.pid,
            ExecutionCreate(
                tc_id=self.case["tc_id"],
                result="fail",
                actual_result="第 51 人仍可提交",
                comments="容量校验未生效",
                tester="李四",
                signature="LS",
            ),
        )

    def tearDown(self) -> None:
        _drop_project(self.pid)

    def test_export_xlsx_sheets_and_fields(self) -> None:
        from io import BytesIO

        from openpyxl import load_workbook

        resp = export_report(self.pid, "xlsx")
        self.assertIn("spreadsheetml", resp.media_type)
        wb = load_workbook(BytesIO(resp.body))

        self.assertEqual(wb.sheetnames, ["概览", "需求清单", "测试用例执行表", "覆盖矩阵"])

        exec_rows = list(wb["测试用例执行表"].values)
        self.assertEqual(exec_rows[0][8], "执行结果")
        self.assertEqual(exec_rows[0][10], "测试comments")
        self.assertEqual(exec_rows[1][8], "失败")
        self.assertEqual(exec_rows[1][9], "第 51 人仍可提交")
        self.assertEqual(exec_rows[1][11], "李四")
        self.assertEqual(exec_rows[1][12], "LS")

        req_rows = list(wb["需求清单"].values)
        self.assertEqual(req_rows[0][0], "需求编号")
        self.assertEqual(req_rows[1][0], "CR-001")

    def test_csv_still_works(self) -> None:
        resp = export_report(self.pid, "csv")
        body = resp.body.decode("utf-8")
        self.assertTrue(body.startswith("\ufeff"))
        self.assertIn("需求清单", body)


if __name__ == "__main__":
    unittest.main()
