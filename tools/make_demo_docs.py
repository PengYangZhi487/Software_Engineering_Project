"""生成演示用的需求文档与 Excel 导入示例。

产物（demo/）：
- 校园选课系统需求_V1.0.docx   段落需求 + 表格需求，覆盖清晰/模糊/冲突/缺验收
- 校园选课系统需求_V1.1.docx   V1.0 改两处数字、加一条、删一条，用于版本比对
- 需求导入示例.xlsx            用于演示「Excel 导入需求」

用法：.\venv\Scripts\python.exe tools\make_demo_docs.py
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo"
OUT.mkdir(exist_ok=True)

INTRO = (
    "本文档用于演示 RATGP 的需求分析与测试用例管理流程，故意包含清晰、模糊、"
    "冲突、缺验收四类需求，以及一段表格形式的需求。"
)

# (编号, 标题, 描述, 验收条件)
ITEMS_V10 = [
    ("CR-001", "登录认证", "学生、教师、管理员分别使用学号/工号与密码登录；连续 5 次失败锁定 10 分钟。",
     "正确密码可登录；连续 5 次失败后锁定 10 分钟"),
    ("CR-002", "课程查询", "学生可按课程名称、教师、院系、上课时间组合查询本学期课程，结果分页每页 20 条。",
     "按任一条件可查到课程；每页 20 条"),
    ("CR-003", "选课时间窗口", "选课窗口为每学期第 1 周周一 8:00 至第 2 周周五 18:00，窗口外不可选课。",
     "窗口内可选课；窗口外提示不在选课时间"),
    ("CR-004", "时间冲突校验", "提交选课时校验同一时间段课程冲突；冲突则拒绝并提示冲突课程。",
     "冲突时拒绝并列出冲突课程；不冲突时允许提交"),
    ("CR-005", "先修课校验", "选课前校验先修课，未通过先修课的学生不得选择该课程。",
     "未通过先修课时拒绝并提示先修课程"),
    ("CR-006", "选课门数上限", "每学期每名学生最多选 6 门课程，第 7 门应拒绝。",
     "已选 6 门时第 7 门被拒绝"),
    ("CR-007", "退课截止", "退课截止时间为第 2 周周五 18:00，截止后不可退课。",
     "截止前可退课；截止后拒绝并提示已过退课时间"),
    ("CR-008", "课程容量", "课程默认容量 50 人，管理员不得扩容；第 51 人选课应拒绝。",
     "容量 50 人时第 51 人拒绝"),
    ("CR-009", "成绩发布后不可改", "成绩录入并发布后不可修改；如需更正走线下审批。",
     "已发布成绩的修改入口不可用；线下审批流程可更正"),
    ("CR-010", "教师开课申请", "教师可提交开课申请，填写课程名、学分、容量、时间、地点、先修课，提交后待审。",
     "提交后状态为待审核"),
    ("CR-011", "管理员审核开课", "管理员可审核开课申请，通过后课程出现在可选课程列表。",
     "审核通过后学生可查到该课程"),
    ("CR-012", "成绩查询", "学生可按学期查询本人各科成绩与绩点。",
     "可查到本学期成绩与绩点"),
    ("CR-013", "选课结果通知", "选课提交后站内通知学生选课结果，并在首页展示。",
     "提交后收到站内通知"),
    ("CR-014", "统计报表导出", "管理员可导出选课人数、课程容量、退课人数统计报表为 Excel。",
     "导出的 Excel 含三类统计"),
    ("CR-015", "系统响应快速", "系统响应快速，查询时无明显等待。",
     "查询无卡顿"),
    ("CR-016", "界面友好美观", "界面简洁友好，操作路径清晰。",
     "新用户可在 5 分钟内完成一次选课"),
    ("CR-017", "通知及时", "选课、退课、成绩发布等事件要及时通知学生。",
     "事件发生后及时收到通知"),
    ("CR-018", "数据每日备份", "系统每天凌晨自动备份选课数据，保留最近 7 天。",
     "每天生成备份；保留 7 天"),
    ("CR-019", "批量导入学生", "管理员可上传学生名单批量导入账号。",
     "导入成功后学生可用学号登录"),
    ("CR-020", "导出个人课表", "学生可导出本学期个人课表为 Excel。",
     "导出文件包含课程、时间、地点"),
    ("CR-021", "课程容量调整", "课程容量统一为 60 人，超过容量后不能选课。",
     "容量 60 人时第 61 人拒绝"),
    ("CR-022", "退课时间说明", "退课截止时间为第 4 周周五 18:00。",
     "第 4 周周五 18:00 前可退课"),
    ("CR-023", "移动端访问", "系统应支持手机浏览器访问选课页面。",
     ""),
    ("CR-024", "公告栏", "系统应提供公告栏，展示选课通知与教学安排。",
     ""),
]

TABLE_V10 = [
    ("REQ-025", "教师调课", "教师可在开课前 3 天提交调课申请，管理员审批后生效。", "审批通过后新课表生效"),
    ("REQ-026", "教室管理", "管理员可维护教室信息，包括楼栋、容量、设备。", "新增教室后可在开课申请中选择"),
    ("REQ-027", "考勤记录", "教师可按课次记录学生出勤，支持迟到/缺勤标记。", "每课次可保存出勤记录"),
]


def _build_doc(path: Path, title: str, items: list[tuple[str, str, str, str]], table: list[tuple[str, str, str, str]]) -> None:
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(INTRO)

    for rid, name, desc, acc in items:
        doc.add_heading(f"{rid} {name}", level=2)
        doc.add_paragraph(desc)
        if acc:
            doc.add_paragraph(f"验收条件：{acc}")

    if table:
        doc.add_heading("附：表格形式的需求", level=2)
        table_obj = doc.add_table(rows=1, cols=4)
        header = table_obj.rows[0].cells
        for idx, text in enumerate(["编号", "需求名称", "描述", "验收条件"]):
            header[idx].text = text
        for row in table:
            cells = table_obj.add_row().cells
            for idx, text in enumerate(row):
                cells[idx].text = text

    doc.save(path)


def _build_xlsx(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "需求清单"
    ws.append(["需求编号", "标题", "描述", "类型", "优先级", "状态", "验收条件"])
    ws.append([
        "", "课程容量（来自 Excel）", "课程容量统一为 55 人，第 56 人拒绝。",
        "功能", "高", "已确认", "第 56 人拒绝",
    ])
    ws.append([
        "", "成绩推送", "成绩发布后向学生推送站内消息。",
        "功能", "中", "未审核", "发布后收到推送",
    ])
    wb.save(path)


def _v11_items() -> list[tuple[str, str, str, str]]:
    items: list[tuple[str, str, str, str]] = []
    for rid, name, desc, acc in ITEMS_V10:
        if rid == "CR-007":
            desc = "退课截止时间为第 4 周周五 18:00，截止后不可退课。"
            acc = "截止前可退课；截止后拒绝并提示已过退课时间"
        if rid == "CR-008":
            desc = "课程默认容量 60 人，管理员不得扩容；第 61 人选课应拒绝。"
            acc = "容量 60 人时第 61 人拒绝"
        if rid == "CR-024":
            continue  # V1.1 删除公告栏，演示 removed
        items.append((rid, name, desc, acc))

    # 新增一条，演示 added
    items.append(("CR-028", "移动端选课", "学生可在手机浏览器完成选课与退课，界面自适应屏幕。",
                  "手机上可完成选课与退课"))
    return items


def main() -> None:
    _build_doc(OUT / "校园选课系统需求_V1.0.docx", "校园选课系统需求说明书 V1.0", ITEMS_V10, TABLE_V10)
    _build_doc(OUT / "校园选课系统需求_V1.1.docx", "校园选课系统需求说明书 V1.1", _v11_items(), TABLE_V10)
    _build_xlsx(OUT / "需求导入示例.xlsx")
    for name in ("校园选课系统需求_V1.0.docx", "校园选课系统需求_V1.1.docx", "需求导入示例.xlsx"):
        path = OUT / name
        print(f"生成: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
