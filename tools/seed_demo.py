"""清空并重建一个可复现的演示项目（不调用大模型）。

用途
----
演示 / 答辩前把数据库恢复成固定状态：

    1 个项目 · 2 个版本文档 · 25 条需求 · 12 条用例
    需求 14 已确认 / 11 未审核，用例 8 已审核 / 3 已生成 / 1 已驳回
    质量问题约 10 条（6 模糊 + 4 冲突）、覆盖率约 43%、变更 2 处

只写数据库，不调 DeepSeek；重复执行结果一致。

用法（在项目根目录）
--------------------
    .\\venv\\Scripts\\python.exe tools\\seed_demo.py --dry-run   # 只看看会做什么
    .\\venv\\Scripts\\python.exe tools\\seed_demo.py --yes       # 执行（自动备份）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docx import Document as DocxDocument  # noqa: E402

from App.dao.db import DB_PATH, get_connection, init_db  # noqa: E402
from App.services.doc_service import parse_document  # noqa: E402
from App.services.quality_scan import scan_requirements  # noqa: E402
from App.services.quality_service import has_ambiguous  # noqa: E402

DATASET = ROOT / "tests" / "datasets" / "course_selection_v1.docx"
UPLOAD_DIR = Path(os.environ.get("RATGP_UPLOAD_DIR") or (ROOT / "App" / "data" / "uploads"))

PROJECT_NAME = "校园选课系统"
PROJECT_DESC = "演示项目：选课系统需求，含清晰 / 模糊 / 冲突三类需求与两版文档"

# (req_id, title, description, type, acceptance, status, para, ratio, raw)
REQUIREMENTS: list[dict] = [
    {"id": "CR-001", "title": "登录认证", "desc": "学生、教师、管理员分别使用学号/工号+密码登录；连续5次失败锁定10分钟。", "type": "functional", "acc": ["学生使用学号+密码登录成功", "教师使用工号+密码登录成功", "管理员使用工号+密码登录成功", "连续5次登录失败后账户锁定10分钟", "锁定期间正确密码也无法登录"], "status": "已确认", "para": 3, "ratio": 0.949, "raw": "学生、教师、管理员分别使用学号/工号+密码登录；连续 5 次失败锁定 10 分钟。"},
    {"id": "CR-002", "title": "课程查询", "desc": "学生可按课程名称、教师、院系、上课时间组合查询本学期课程，结果分页每页20条。", "type": "functional", "acc": ["支持按课程名称、教师、院系、上课时间的任意组合查询", "查询结果仅包含本学期课程", "结果分页展示，每页20条"], "status": "已确认", "para": 5, "ratio": 0.975, "raw": "学生可按课程名称、教师、院系、上课时间组合查询本学期课程，结果分页每页 20 条。"},
    {"id": "CR-003", "title": "选课时间窗口", "desc": "选课窗口为每学期第1周周一8:00至第2周周五18:00，窗口外不可选课。", "type": "functional", "acc": ["窗口内允许选课", "窗口开始前拒绝选课", "窗口结束后拒绝选课"], "status": "已确认", "para": 7, "ratio": 0.914, "raw": "选课窗口为每学期第 1 周周一 8:00 至第 2 周周五 18:00，窗口外不可选课。"},
    {"id": "CR-004", "title": "时间冲突校验", "desc": "提交选课时校验同一时间段课程冲突；冲突则拒绝并提示冲突课程。", "type": "functional", "acc": ["选课时间与已选课程无冲突时允许提交", "存在时间冲突时拒绝选课", "拒绝时提示具体冲突课程"], "status": "已确认", "para": 9, "ratio": 1.0, "raw": "提交选课时校验同一时间段课程冲突；冲突则拒绝并提示冲突课程。"},
    {"id": "CR-005", "title": "先修课校验", "desc": "选课前校验先修课，未通过先修课的学生不得选择该课程。", "type": "functional", "acc": ["已通过先修课的学生允许选课", "未通过先修课的学生拒绝选课"], "status": "已确认", "para": 11, "ratio": 1.0, "raw": "选课前校验先修课，未通过先修课的学生不得选择该课程。"},
    {"id": "CR-006", "title": "选课门数上限", "desc": "每学期每名学生最多选6门课程，第7门应拒绝。", "type": "functional", "acc": ["已选课程少于6门时允许选课", "已选课程达到6门时拒绝第7门选课"], "status": "已确认", "para": 13, "ratio": 0.917, "raw": "每学期每名学生最多选 6 门课程，第 7 门应拒绝。"},
    {"id": "CR-007", "title": "退课截止", "desc": "退课截止时间为第2周周五18:00，截止后不可退课。", "type": "functional", "acc": ["截止时间前允许退课", "截止时间后拒绝退课"], "status": "已确认", "para": 15, "ratio": 0.945, "raw": "退课截止时间为第 2 周周五 18:00，截止后不可退课。"},
    {"id": "CR-008", "title": "课程容量", "desc": "课程默认容量50人，管理员不得扩容；第51人选课应拒绝。", "type": "functional", "acc": ["课程默认容量为50人", "已选人数小于50时允许选课", "已选人数达到50时拒绝第51人选课", "管理员无法扩容课程容量"], "status": "已确认", "para": 17, "ratio": 0.933, "raw": "课程默认容量 50 人，管理员不得扩容；第 51 人选课应拒绝。"},
    {"id": "CR-009", "title": "成绩发布后不可改", "desc": "成绩录入并发布后不可修改；如需更正走线下审批。", "type": "functional", "acc": ["成绩发布前允许修改", "成绩发布后拒绝修改", "成绩发布后提供线下审批更正说明"], "status": "已确认", "para": 19, "ratio": 1.0, "raw": "成绩录入并发布后不可修改；如需更正走线下审批。"},
    {"id": "CR-010", "title": "教师开课申请", "desc": "教师可提交开课申请，填写课程名、学分、容量、时间、地点、先修课，提交后待审。", "type": "functional", "acc": ["教师可填写课程名、学分、容量、时间、地点、先修课并提交", "提交后申请状态为待审核"], "status": "已确认", "para": 21, "ratio": 1.0, "raw": "教师可提交开课申请，填写课程名、学分、容量、时间、地点、先修课，提交后待审。"},
    {"id": "CR-011", "title": "管理员审核开课", "desc": "管理员审核开课申请，通过后课程进入可选列表；拒绝需填写原因。", "type": "functional", "acc": ["管理员可通过开课申请，通过后课程进入可选列表", "管理员可拒绝开课申请，拒绝时必须填写原因"], "status": "已确认", "para": 23, "ratio": 1.0, "raw": "管理员审核开课申请，通过后课程进入可选列表；拒绝需填写原因。"},
    {"id": "CR-012", "title": "成绩查询", "desc": "学生可查询本人已选课程和已发布成绩，不能查看他人成绩。", "type": "functional", "acc": ["学生可查询本人已选课程", "学生可查询本人已发布成绩", "学生无法查看他人成绩"], "status": "已确认", "para": 25, "ratio": 1.0, "raw": "学生可查询本人已选课程和已发布成绩，不能查看他人成绩。"},
    {"id": "CR-013", "title": "选课结果通知", "desc": "选课结果生成后5分钟内发送站内信，失败重试3次。", "type": "functional", "acc": ["选课结果生成后5分钟内发送站内信", "发送失败时重试最多3次"], "status": "已确认", "para": 27, "ratio": 0.923, "raw": "选课结果生成后 5 分钟内发送站内信，失败重试 3 次。"},
    {"id": "CR-014", "title": "统计报表导出", "desc": "管理员可导出选课统计CSV，字段含课程、容量、已选人数、选课率，使用UTF-8 BOM。", "type": "functional", "acc": ["管理员可导出选课统计CSV", "CSV字段包含课程、容量、已选人数、选课率", "CSV文件使用UTF-8 BOM编码"], "status": "已确认", "para": 29, "ratio": 0.978, "raw": "管理员可导出选课统计 CSV，字段含课程、容量、已选人数、选课率，使用 UTF-8 BOM。"},
    {"id": "CR-015", "title": "系统响应快速", "desc": "系统响应快速，学生查询课程时无明显等待。", "type": "non_functional", "acc": ["学生查询课程时无明显等待（需进一步量化响应时间指标）"], "status": "未审核", "para": 31, "ratio": 1.0, "raw": "系统响应快速，学生查询课程时无明显等待。"},
    {"id": "CR-016", "title": "界面友好美观", "desc": "系统界面友好美观，操作便捷。", "type": "non_functional", "acc": ["界面友好美观、操作便捷（需进一步明确可度量标准）"], "status": "未审核", "para": 33, "ratio": 1.0, "raw": "系统界面友好美观，操作便捷。"},
    {"id": "CR-017", "title": "通知及时", "desc": "选课结果通知应及时，确保学生尽快知晓。", "type": "non_functional", "acc": ["选课结果通知及时送达（需进一步量化时限指标）"], "status": "未审核", "para": 35, "ratio": 1.0, "raw": "选课结果通知应及时，确保学生尽快知晓。"},
    {"id": "CR-018", "title": "课程推荐合理", "desc": "系统能根据学生兴趣推荐合理课程。", "type": "functional", "acc": ["系统根据学生兴趣推荐课程（需进一步明确推荐合理性标准）"], "status": "未审核", "para": 37, "ratio": 1.0, "raw": "系统能根据学生兴趣推荐合理课程。"},
    {"id": "CR-019", "title": "高并发稳定", "desc": "系统在高并发选课期间保持稳定。", "type": "non_functional", "acc": ["高并发选课期间系统保持稳定（需进一步量化并发量与稳定性指标）"], "status": "未审核", "para": 39, "ratio": 1.0, "raw": "系统在高并发选课期间保持稳定。"},
    {"id": "CR-020", "title": "选课公平高效", "desc": "选课过程应公平高效，避免拥堵。", "type": "non_functional", "acc": ["选课过程公平高效、避免拥堵（需进一步明确公平与效率的度量标准）"], "status": "未审核", "para": 41, "ratio": 1.0, "raw": "选课过程应公平高效，避免拥堵。"},
    {"id": "CR-021", "title": "允许选8门", "desc": "允许学生每学期选8门课程。", "type": "functional", "acc": ["学生每学期可选8门课程（与CR-006最多6门矛盾，需澄清）"], "status": "未审核", "para": 43, "ratio": 0.929, "raw": "允许学生每学期选 8 门课程。"},
    {"id": "CR-022", "title": "四周内可退课", "desc": "开学后4周内学生可无条件退课。", "type": "functional", "acc": ["开学后4周内允许无条件退课（与CR-007第2周周五18:00截止矛盾，需澄清）"], "status": "未审核", "para": 45, "ratio": 0.938, "raw": "开学后 4 周内学生可无条件退课。"},
    {"id": "CR-023", "title": "热门课程自动扩容", "desc": "热门课程可根据选课人数自动扩容至100人。", "type": "functional", "acc": ["热门课程根据选课人数自动扩容至100人（与CR-008默认容量50且不得扩容矛盾，需澄清）"], "status": "未审核", "para": 47, "ratio": 0.955, "raw": "热门课程可根据选课人数自动扩容至 100 人。"},
    {"id": "CR-024", "title": "成绩7天内可改", "desc": "教师可在成绩发布后7天内任意修改成绩。", "type": "functional", "acc": ["成绩发布后7天内教师可修改成绩（与CR-009发布后不可改矛盾，需澄清）"], "status": "未审核", "para": 49, "ratio": 0.95, "raw": "教师可在成绩发布后 7 天内任意修改成绩。"},
    {"id": "CR-025", "title": "容量无限扩容", "desc": "课程容量可根据需求无限扩容。", "type": "functional", "acc": ["课程容量可根据需求无限扩容（与CR-008不得扩容、CR-023扩容至100人矛盾，需澄清）"], "status": "未审核", "para": 51, "ratio": 1.0, "raw": "课程容量可根据需求无限扩容。"},
]

# (req_id, title, preconditions, steps, expected, test_type, status)
CASES: list[dict] = [
    {"req_id": "CR-001", "title": "教师登录成功并校验角色权限", "pre": ["教师账号已注册", "密码正确"], "steps": ["输入工号和密码", "点击登录"], "expected": "登录成功，进入教师工作台", "type": "normal", "status": "已审核"},
    {"req_id": "CR-001", "title": "连续 5 次失败后锁定账户 10 分钟", "pre": ["账号未被锁定", "密码错误"], "steps": ["连续 5 次输入错误密码", "第 6 次输入正确密码"], "expected": "账户锁定 10 分钟，第 6 次仍拒绝登录", "type": "abnormal", "status": "已审核"},
    {"req_id": "CR-002", "title": "按课程名 / 教师 / 院系组合查询并分页", "pre": ["学生已登录", "本学期有课程"], "steps": ["按课程名 + 教师 + 院系组合查询"], "expected": "返回匹配课程，分页每页 20 条", "type": "normal", "status": "已生成"},
    {"req_id": "CR-003", "title": "选课窗口开始前提交被拒", "pre": ["当前时间早于选课窗口"], "steps": ["学生提交选课请求"], "expected": "拒绝并提示选课窗口未开始", "type": "abnormal", "status": "已审核"},
    {"req_id": "CR-006", "title": "已选 6 门后提交第 7 门被拒", "pre": ["学生已选 6 门课程"], "steps": ["提交第 7 门选课请求"], "expected": "拒绝并提示超出每学期选课上限", "type": "boundary", "status": "已审核"},
    {"req_id": "CR-007", "title": "退课截止时间边界：18:00 前与后", "pre": ["学生已选课程", "当天为第 2 周周五"], "steps": ["18:00 前提交退课", "18:00 后提交退课"], "expected": "18:00 前退课成功，18:00 后拒绝退课", "type": "boundary", "status": "已审核"},
    {"req_id": "CR-008", "title": "容量 50 人上限边界", "pre": ["课程已选 49 人"], "steps": ["第 50 人提交选课", "第 51 人提交选课"], "expected": "第 50 人成功，第 51 人拒绝并提示课程已满", "type": "boundary", "status": "已审核"},
    {"req_id": "CR-009", "title": "成绩发布后修改被拒", "pre": ["成绩已发布"], "steps": ["教师提交修改成绩请求"], "expected": "拒绝并提示走线下审批", "type": "abnormal", "status": "已审核"},
    {"req_id": "CR-012", "title": "学生仅能查询本人成绩", "pre": ["学生 A 已登录", "学生 B 有已发布成绩"], "steps": ["学生 A 尝试访问学生 B 的成绩"], "expected": "拒绝访问，只能查看本人成绩", "type": "abnormal", "status": "已生成"},
    {"req_id": "CR-010", "title": "开课申请必填项校验", "pre": ["教师已登录"], "steps": ["不填学分提交开课申请"], "expected": "拒绝提交并提示学分必填", "type": "abnormal", "status": "已生成"},
    {"req_id": "CR-014", "title": "统计 CSV 导出字段与 UTF-8 BOM", "pre": ["管理员已登录", "已有选课数据"], "steps": ["导出选课统计 CSV"], "expected": "CSV 含课程 / 容量 / 已选人数 / 选课率，UTF-8 BOM 编码", "type": "normal", "status": "已生成"},
    {"req_id": "CR-011", "title": "审核拒绝必须填写原因", "pre": ["存在待审核的开课申请"], "steps": ["管理员拒绝但不填原因"], "expected": "拒绝操作并提示原因必填", "type": "abnormal", "status": "已驳回"},
]


def _prepare_documents() -> tuple[Path, Path, int]:
    """复制 V1.0，并生成一份改了两处数字的 V1.1。"""
    if not DATASET.exists():
        raise SystemExit(f"缺少测试数据集：{DATASET}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    v1 = UPLOAD_DIR / f"{uuid.uuid4().hex}.docx"
    shutil.copy2(DATASET, v1)

    doc = DocxDocument(v1)
    changed = 0
    for para in doc.paragraphs:
        if "课程默认容量" in para.text:
            new_text = para.text.replace("50 人", "60 人").replace("第 51 人", "第 61 人")
            if new_text != para.text:
                para.text = new_text
                changed += 1
        elif "退课截止时间" in para.text:
            new_text = para.text.replace("第 2 周", "第 4 周")
            if new_text != para.text:
                para.text = new_text
                changed += 1

    v2 = UPLOAD_DIR / f"{uuid.uuid4().hex}.docx"
    doc.save(v2)
    if changed != 2:
        raise SystemExit(f"V1.1 生成异常：只改了 {changed} 处（预期 2 处）")
    return v1, v2, changed


def _insert_document(conn, project_id: int, path: Path, filename: str, version: str) -> int:
    text, para_index = parse_document(str(path))
    cur = conn.execute(
        """
        INSERT INTO Document (project_id, filename, version, content_text, para_index, file_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (project_id, filename, version, text,
         json.dumps(para_index, ensure_ascii=False), str(path)),
    )
    return int(cur.lastrowid)


def _reset(conn) -> dict:
    """按外键顺序清空业务表，保留 User。"""
    counts = {}
    for table in ("ChangeLog", "RequirementTestLink", "TestCase",
                  "Requirement", "Document", "Project"):
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.execute(f"DELETE FROM {table}")
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN "
        "('ChangeLog','RequirementTestLink','TestCase','Requirement','Document','Project')"
    )
    return counts


def _seed(conn) -> dict:
    cur = conn.execute(
        "INSERT INTO Project (project_name, description) VALUES (?, ?)",
        (PROJECT_NAME, PROJECT_DESC),
    )
    project_id = int(cur.lastrowid)

    v1, v2, changed = _prepare_documents()
    doc_v1 = _insert_document(conn, project_id, v1, DATASET.name, "V1.0")
    doc_v2 = _insert_document(conn, project_id, v2, "course_selection_v1.1.docx", "V1.1")

    for req in REQUIREMENTS:
        location = {"para_no": req["para"], "raw": req["raw"], "ratio": req["ratio"]}
        ambiguous = 1 if has_ambiguous(f"{req['title']} {req['desc']}") else 0
        conn.execute(
            """
            INSERT INTO Requirement
                (req_id, project_id, doc_id, title, description, acceptance,
                 req_type, status, source_location, is_ambiguous)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (req["id"], project_id, doc_v1, req["title"], req["desc"],
             json.dumps(req["acc"], ensure_ascii=False), req["type"], req["status"],
             json.dumps(location, ensure_ascii=False), ambiguous),
        )

    for case in CASES:
        cur = conn.execute(
            """
            INSERT INTO TestCase
                (project_id, req_id, title, preconditions, steps,
                 expected_result, test_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, case["req_id"], case["title"],
             json.dumps(case["pre"], ensure_ascii=False),
             json.dumps(case["steps"], ensure_ascii=False),
             case["expected"], case["type"], case["status"]),
        )
        conn.execute(
            "INSERT INTO RequirementTestLink (project_id, req_id, tc_id, link_source) "
            "VALUES (?, ?, ?, '人工')",
            (project_id, case["req_id"], int(cur.lastrowid)),
        )

    return {"project_id": project_id, "documents": 2, "changed_paragraphs": changed}


def _stats(conn, project_id: int) -> dict:
    req_rows = conn.execute(
        "SELECT req_id, title, description, acceptance, status, is_ambiguous "
        "FROM Requirement WHERE project_id = ?", (project_id,)
    ).fetchall()
    issues = scan_requirements([
        {"req_id": r["req_id"], "title": r["title"], "description": r["description"],
         "acceptance": json.loads(r["acceptance"] or "[]"), "is_ambiguous": r["is_ambiguous"]}
        for r in req_rows
    ])
    by_kind: dict[str, int] = {}
    for issue in issues:
        by_kind[issue["kind"]] = by_kind.get(issue["kind"], 0) + 1

    req_status = dict(conn.execute(
        "SELECT status, COUNT(*) FROM Requirement WHERE project_id = ? GROUP BY status",
        (project_id,),
    ).fetchall())
    case_status = dict(conn.execute(
        "SELECT status, COUNT(*) FROM TestCase WHERE project_id = ? GROUP BY status",
        (project_id,),
    ).fetchall())

    confirmed = conn.execute(
        "SELECT COUNT(*) FROM Requirement WHERE project_id = ? AND status = '已确认'",
        (project_id,),
    ).fetchone()[0]
    covered = conn.execute(
        """
        SELECT COUNT(DISTINCT r.req_id)
        FROM Requirement r
        JOIN RequirementTestLink l ON l.project_id = r.project_id AND l.req_id = r.req_id
        JOIN TestCase tc ON tc.tc_id = l.tc_id
        WHERE r.project_id = ? AND r.status = '已确认' AND tc.status = '已审核'
        """,
        (project_id,),
    ).fetchone()[0]

    return {
        "requirements": len(req_rows),
        "req_status": req_status,
        "cases": sum(case_status.values()),
        "case_status": case_status,
        "issues": len(issues),
        "issue_kinds": by_kind,
        "confirmed": confirmed,
        "covered": covered,
        "coverage_pct": round(covered / confirmed * 100) if confirmed else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="清空并重建演示数据（不调用大模型）")
    parser.add_argument("--yes", action="store_true", help="确认执行（会删除现有业务数据）")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不改数据库")
    parser.add_argument("--no-backup", action="store_true", help="不备份现有数据库")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"数据库：{DB_PATH}")
    init_db()

    conn = get_connection()
    try:
        before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("Project", "Document", "Requirement", "TestCase")}
        print(f"当前数据：{before}")

        if args.dry_run:
            print("dry-run：将清空上述业务表，并重建 "
                  f"{len(REQUIREMENTS)} 条需求 / {len(CASES)} 条用例 / 2 个版本文档。")
            return 0
        if not args.yes:
            print("未执行。加 --yes 确认，或先用 --dry-run 查看计划。")
            return 2

        if not args.no_backup:
            backup = Path(f"{DB_PATH}.bak-{datetime.now():%Y%m%d-%H%M%S}")
            shutil.copy2(DB_PATH, backup)
            print(f"已备份到：{backup}")

        _reset(conn)
        result = _seed(conn)
        conn.commit()
        stats = _stats(conn, result["project_id"])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n=== 演示数据已重建 ===")
    print(f"项目 id：{result['project_id']}（前端固定读 1，重置后应为 1）")
    print(f"文档：2 个版本，V1.1 改动 {result['changed_paragraphs']} 处数字")
    print(f"需求：{stats['requirements']} 条，状态 {stats['req_status']}")
    print(f"用例：{stats['cases']} 条，状态 {stats['case_status']}")
    print(f"质量问题：{stats['issues']} 条 {stats['issue_kinds']}")
    print(f"覆盖率：{stats['covered']}/{stats['confirmed']} = {stats['coverage_pct']}%")
    print("\n打开 http://localhost:3000 查看；建议先到「需求」页确认几条，再看「用例 / 追踪 / 变更 / 报告」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
