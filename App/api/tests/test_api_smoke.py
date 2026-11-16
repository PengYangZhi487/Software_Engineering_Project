"""接口冒烟测试：不依赖 httpx / TestClient，直接调用路由函数。

运行：
    cd Software_Engineering_Project
    venv\\Scripts\\python.exe -m unittest discover -s App/api/tests -v
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import unittest
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
    generate_cases as api_generate_cases,
    list_cases as api_list_cases,
    update_case,
)
from App.api.routers.documents import upload_document  # noqa: E402
from App.api.routers.diff import document_diff  # noqa: E402
from App.api.routers.trace import get_coverage, get_trace  # noqa: E402
from App.api.routers.requirements import (  # noqa: E402
    extract_requirements,
    list_requirements,
    update_requirement,
)
from App.api.schemas import (  # noqa: E402
    CaseGenerateRequest,
    CaseStatusUpdate,
    RequirementStatusUpdate,
)
from App.dao.db import get_connection, init_db  # noqa: E402
from App.services import case_service, llm_service  # noqa: E402
from App.services.doc_service import parse_document  # noqa: E402
from App.services.diff_service import diff_paragraphs  # noqa: E402
from App.services.quality_scan import scan_requirements  # noqa: E402

DOCX = ROOT / "test_file" / "datasets" / "course_selection_v1.docx"
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


def _upload(data: bytes, filename: str, version: str = "V1.0"):
    up = UploadFile(filename=filename, file=io.BytesIO(data))
    return asyncio.run(upload_document(PROJECT_ID, up, version))


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
        self.assertIn("/api/requirements/{req_id}", paths)
        self.assertIn("/api/projects/{project_id}/quality/issues", paths)
        self.assertIn("/api/projects/{project_id}/cases", paths)
        self.assertIn("/api/projects/{project_id}/cases/generate", paths)
        self.assertIn("/api/cases/{tc_id}", paths)
        self.assertIn("/api/projects/{project_id}/trace", paths)
        self.assertIn("/api/projects/{project_id}/trace/coverage", paths)
        self.assertIn("/api/projects/{project_id}/document-diff", paths)

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
        self.assertTrue(Path(resp.document.file_path).exists(), "原始文件应落盘保留")

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
            result = extract_requirements(PROJECT_ID, None, True)

        # 编号由程序生成，不采信模型给的 X-1 / X-2
        self.assertEqual([item.req_id for item in result.items], ["CR-001", "CR-002"])
        self.assertEqual(result.created, 2)
        self.assertEqual(result.replaced, True)
        self.assertTrue(result.items[1].is_ambiguous, "「快速」「明显」应被标为模糊")
        self.assertEqual(result.items[0].status, "未审核")

        confirmed = update_requirement("CR-001", RequirementStatusUpdate(status="已确认"))
        self.assertEqual(confirmed.status, "已确认")

        rejected = update_requirement("CR-002", RequirementStatusUpdate(status="已驳回"))
        self.assertEqual(rejected.status, "已驳回")

        listing = list_requirements(PROJECT_ID, None)
        self.assertEqual(listing.total, 2)
        self.assertEqual(listing.confirmed, 1)
        self.assertEqual(listing.ambiguous, 1)

        with self.assertRaises(HTTPException) as missing:
            update_requirement("CR-999", RequirementStatusUpdate(status="已确认"))
        self.assertEqual(missing.exception.status_code, 404)

        with self.assertRaises(HTTPException) as illegal:
            update_requirement("CR-001", RequirementStatusUpdate(status="随便"))
        self.assertEqual(illegal.exception.status_code, 422)

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
            extract_requirements(empty_project, None, True)
        self.assertEqual(ctx.exception.status_code, 400)


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
            conn.execute("DELETE FROM Requirement WHERE req_id = 'CR-901'")
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
            result = api_generate_cases(PROJECT_ID, CaseGenerateRequest(replace=True))

        # CR-999 会因外键约束写不进去，计入 skipped
        self.assertEqual(result.created, 2)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.by_type, {"normal": 1, "boundary": 1})
        self.assertIn("CR-901", result.req_ids)

        listing = api_list_cases(PROJECT_ID)
        self.assertGreaterEqual(listing.total, 2)
        self.assertEqual(listing.by_status.get("已生成"), 2)
        case = listing.items[0]

        reviewed = update_case(case.tc_id, CaseStatusUpdate(status="已审核"))
        self.assertEqual(reviewed.status, "已审核")

        rejected = update_case(case.tc_id, CaseStatusUpdate(status="已驳回"))
        self.assertEqual(rejected.status, "已驳回")

        with self.assertRaises(HTTPException) as missing:
            update_case(999999, CaseStatusUpdate(status="已审核"))
        self.assertEqual(missing.exception.status_code, 404)

        with self.assertRaises(HTTPException) as illegal:
            update_case(case.tc_id, CaseStatusUpdate(status="随便"))
        self.assertEqual(illegal.exception.status_code, 422)

    def test_generate_requires_confirmed(self) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE Requirement SET status = '未审核' WHERE project_id = ?", (PROJECT_ID,))
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(HTTPException) as ctx:
            api_generate_cases(PROJECT_ID, CaseGenerateRequest())
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
            conn.execute("UPDATE Requirement SET status = '已确认' WHERE req_id = 'CR-901'")
            conn.execute("DELETE FROM RequirementTestLink")
            conn.execute("DELETE FROM TestCase")
            cur = conn.execute(
                "INSERT INTO TestCase (req_id, title, steps, expected_result, test_type, status) "
                "VALUES ('CR-901', '容量边界', '[\"提交选课\"]', '拒绝', 'boundary', '已审核')"
            )
            conn.execute(
                "INSERT INTO RequirementTestLink (req_id, tc_id, link_source) VALUES ('CR-901', ?, 'AI')",
                (cur.lastrowid,),
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

        update_case(tc_id, CaseStatusUpdate(status="已驳回"))
        cov = get_coverage(PROJECT_ID)
        self.assertEqual(cov.covered, 0)
        self.assertEqual(cov.coverage_pct, 0)
        self.assertTrue(cov.consistent)

        update_case(tc_id, CaseStatusUpdate(status="已审核"))
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
                "INSERT INTO TestCase (req_id, title, steps, expected_result, test_type, status) "
                "VALUES ('CR-950', '容量边界', '[]', '拒绝', 'boundary', '已审核')"
            ).lastrowid
            conn.execute(
                "INSERT INTO RequirementTestLink (req_id, tc_id, link_source) VALUES ('CR-950', ?, 'AI')",
                (case_id,),
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


if __name__ == "__main__":
    unittest.main()
