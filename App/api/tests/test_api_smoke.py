"""接口冒烟测试：不依赖 httpx / TestClient，直接调用路由函数。

运行：
    cd Software_Engineering_Project
    venv\\Scripts\\python.exe -m unittest discover -s App/api/tests -v
"""
from __future__ import annotations

import asyncio
import io
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
from App.api.routers.documents import upload_document  # noqa: E402
from App.api.routers.requirements import (  # noqa: E402
    extract_requirements,
    list_requirements,
    update_requirement,
)
from App.api.schemas import RequirementStatusUpdate  # noqa: E402
from App.dao.db import get_connection, init_db  # noqa: E402
from App.services import llm_service  # noqa: E402
from App.services.doc_service import parse_document  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
