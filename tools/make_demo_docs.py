"""生成演示用的需求文档与 Excel 导入示例（图书馆借阅管理系统）。

文档刻意写成「普通需求分析文档」：按章节组织、用自然段落描述需求，
没有每条需求一个标题/验收条件的结构化格式；同时保留真实的模糊表述、
数值冲突、缺验收条件，以及两张表格（权限表、借阅状态表）。

产物（demo/）：
- 图书馆借阅系统需求_V1.0.docx
- 图书馆借阅系统需求_V1.1.docx   （改两处数字、新增座位预约、删除公告栏）
- 需求导入示例.xlsx

用法：.\venv\Scripts\python.exe tools\make_demo_docs.py
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo"
OUT.mkdir(exist_ok=True)

PERMISSION_TABLE = [
    ("角色", "主要职责", "权限范围"),
    ("读者", "查询、借阅、续借、预约、查看借阅记录", "馆藏查询、本人借阅记录、预约"),
    ("图书馆管理员", "图书入库、借还处理、读者管理、统计报表", "全部图书与借阅数据"),
    ("系统管理员", "账号权限、系统配置、操作日志", "系统设置与全部数据"),
]

STATUS_TABLE = [
    ("状态", "说明", "是否可借"),
    ("在架", "图书在馆且可借", "是"),
    ("借出", "已被读者借走", "否"),
    ("预约中", "已被读者预约，保留 3 天", "否"),
    ("下架", "图书停用或丢失", "否"),
]


def _blocks_v10() -> list[tuple[str, object]]:
    return [
        ("h1", "图书馆借阅管理系统需求分析说明书 V1.0"),
        ("h2", "一、项目背景与目标"),
        ("p", "学校图书馆现有纸质藏书约 30 万册，目前借还书依赖人工登记，高峰期读者排队严重，"
              "也无法在线查询馆藏和借阅记录。为提高借阅效率、方便读者，学校计划建设一套图书馆借阅管理系统，"
              "覆盖图书入库、馆藏检索、借阅、续借、预约、归还、逾期处理和统计报表等环节。"),
        ("h2", "二、用户角色与权限"),
        ("p", "系统面向三类用户：读者（学生和教师）、图书馆管理员、系统管理员。"
              "读者可以查询馆藏、借阅、续借、预约和查看个人借阅记录；"
              "图书馆管理员负责图书入库、借还处理、读者管理和统计报表；"
              "系统管理员负责账号、权限和系统配置。权限划分如下表所示。"),
        ("table", PERMISSION_TABLE),
        ("h2", "三、功能需求"),
        ("h3", "3.1 馆藏查询"),
        ("p", "读者可以按书名、作者、ISBN、分类等条件查询馆藏图书，查询结果应显示图书状态（在架、借出、预约中）。"
              "系统应支持模糊搜索和分页展示，每页显示 20 条记录，并按相关度排序。"),
        ("h3", "3.2 图书借阅"),
        ("p", "读者凭校园卡在自助借还机或服务台办理借阅。每位读者最多可同时借阅 5 册图书，"
              "借阅期限为 30 天；到期前可以续借一次。借阅成功后系统记录借阅时间、应还时间和操作人。"),
        ("h3", "3.3 图书续借"),
        ("p", "读者可在到期前通过系统办理续借，每册图书只能续借一次，续借后应还日期顺延 15 天。"
              "如果该书已被其他读者预约，则不允许续借，系统应提示读者。"),
        ("h3", "3.4 预约管理"),
        ("p", "对于已借出的图书，读者可以预约；预约成功后，系统在图书归还时通知读者。"
              "读者应在收到通知后 3 天内到馆取书，逾期未取系统自动取消预约。"
              "热门图书的预约人数不宜过多，系统应合理控制预约队列。"),
        ("h3", "3.5 归还与逾期处理"),
        ("p", "读者归还图书时，系统自动计算是否逾期。逾期按每天 0.2 元收取滞纳金，单册图书滞纳金上限为 20 元。"
              "逾期未还超过 30 天的图书，系统应暂停该读者的借阅权限，直到图书归还并缴清滞纳金。"),
        ("h3", "3.6 图书管理"),
        ("p", "图书馆管理员可以进行图书入库、上架、下架和信息修改，支持通过 Excel 批量导入图书信息。"
              "图书信息包括书名、作者、ISBN、出版社、出版日期、分类、馆藏位置和复本数量。"),
        ("h3", "3.7 读者管理"),
        ("p", "管理员可以新增、修改、停用读者账号，查看读者的借阅记录和逾期记录。"
              "读者信息包括学号/工号、姓名、院系、联系方式和账号状态。"),
        ("h3", "3.8 通知服务"),
        ("p", "系统在借阅成功、到期提醒、预约到馆和逾期等节点向读者发送站内通知。"
              "通知要及时送达，重要通知应支持短信提醒。"),
        ("h3", "3.9 统计报表"),
        ("p", "管理员可以导出借阅量、热门图书、逾期情况和读者活跃度等统计报表，支持按时间段筛选，报表格式为 Excel。"),
        ("h3", "3.10 系统设置"),
        ("p", "系统管理员可以维护图书馆开放时间、借阅规则、罚款规则和通知模板。"
              "罚款规则默认为每天 0.5 元。系统应提供操作日志，记录管理员的关键操作。"),
        ("h3", "3.11 公告与推荐"),
        ("p", "系统应提供公告栏，展示图书馆通知和活动信息；同时根据借阅记录向读者推荐相关图书。"),
        ("h2", "四、非功能需求"),
        ("p", "系统查询响应要快速，读者在馆藏检索时不应有明显等待。"),
        ("p", "界面应简洁友好，新读者能够快速上手，不经过培训也能完成一次借阅。"),
        ("p", "系统应保证读者信息和借阅数据的安全，重要数据需要加密存储，并定期备份。"),
        ("p", "系统应兼容主流浏览器，并支持手机浏览器访问基本查询功能。"),
        ("h2", "五、数据需求"),
        ("p", "系统需要保存图书信息、读者信息、借阅记录、预约记录、罚款记录和操作日志。"
              "借阅记录应能追溯借阅人、图书、借阅时间、归还时间和操作员。"
              "数据每日凌晨自动备份，保留最近 30 天。"),
        ("h2", "六、约束与假设"),
        ("p", "系统部署在学校内网，读者使用校园卡认证。图书馆现有图书数据需要一次性导入，导入格式为 Excel。"
              "系统上线后，原有纸质登记流程并行运行一个月后停用。"),
        ("h2", "七、附录：借阅状态说明"),
        ("p", "借阅状态用于描述图书当前的可借情况，具体如下表所示。"),
        ("table", STATUS_TABLE),
    ]


def _blocks_v11() -> list[tuple[str, object]]:
    blocks = list(_blocks_v10())
    result: list[tuple[str, object]] = []
    for kind, value in blocks:
        if kind == "h1":
            value = "图书馆借阅管理系统需求分析说明书 V1.1"
        if kind == "p" and isinstance(value, str):
            if "借阅期限为 30 天" in value:
                value = value.replace("借阅期限为 30 天", "借阅期限为 45 天")
            if "逾期按每天 0.2 元" in value:
                value = value.replace("逾期按每天 0.2 元", "逾期按每天 0.5 元")
        if kind == "h3" and value == "3.11 公告与推荐":
            continue  # V1.1 删除，演示 removed
        if kind == "p" and isinstance(value, str) and "公告栏" in value:
            continue  # 删除公告栏对应的描述
        result.append((kind, value))

    # 新增一节，演示 added
    idx = next(i for i, (k, v) in enumerate(result) if k == "h2" and v == "四、非功能需求")
    result[idx:idx] = [
        ("h3", "3.12 座位预约"),
        ("p", "读者可以查看图书馆各阅览室的座位使用情况，并提前预约座位。"
               "每个读者每天最多预约 2 个时段，每个时段 2 小时；"
               "预约成功后需在开始时间前 15 分钟签到，否则取消预约。"),
    ]
    return result


def _build_doc(path: Path, blocks: list[tuple[str, object]]) -> None:
    doc = Document()
    for kind, value in blocks:
        if kind == "h1":
            doc.add_heading(str(value), level=1)
        elif kind == "h2":
            doc.add_heading(str(value), level=2)
        elif kind == "h3":
            doc.add_heading(str(value), level=3)
        elif kind == "p":
            doc.add_paragraph(str(value))
        elif kind == "table":
            rows = value  # type: ignore[assignment]
            table = doc.add_table(rows=1, cols=len(rows[0]))
            header = table.rows[0].cells
            for i, text in enumerate(rows[0]):
                header[i].text = str(text)
            for row in rows[1:]:
                cells = table.add_row().cells
                for i, text in enumerate(row):
                    cells[i].text = str(text)
    doc.save(path)


def _build_xlsx(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "需求清单"
    ws.append(["需求编号", "标题", "描述", "类型", "优先级", "状态", "验收条件"])
    ws.append([
        "", "新书采购审批", "图书馆采购新书前需提交采购申请，由馆长审批后进入采购流程。",
        "功能", "高", "已确认", "审批通过后生成采购单",
    ])
    ws.append([
        "", "馆际互借", "读者可申请从合作图书馆借阅图书，借期 30 天。",
        "功能", "中", "未审核", "申请通过后可借阅",
    ])
    wb.save(path)


def main() -> None:
    _build_doc(OUT / "图书馆借阅系统需求_V1.0.docx", _blocks_v10())
    _build_doc(OUT / "图书馆借阅系统需求_V1.1.docx", _blocks_v11())
    _build_xlsx(OUT / "需求导入示例.xlsx")
    for name in ("图书馆借阅系统需求_V1.0.docx", "图书馆借阅系统需求_V1.1.docx", "需求导入示例.xlsx"):
        path = OUT / name
        print(f"生成: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
