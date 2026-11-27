"""生成《软件工程》课程项目实践作业提交材料目录。

按作业要求的分类整理：
- 01 项目实践报告（可编辑 docx）
- 02 技术文档（需求分析 / 详细设计 / 概要设计 / 交接指南 / 封装说明 / 演示相关）
- 03 项目管理与协作（项目管理记录.xlsx、问题解决过程日志.docx、团队协作记录.docx）
- 04 可编辑制品源文件（preview.html、tokens.json、架构图/ER 图 drawio、界面截图）
- 05 软件成果（RATGP.exe、便携 zip、源码 zip、演示数据库、演示文档）
- 06 视频（待录说明）
- 00_提交说明.md

用法：.\venv\Scripts\python.exe tools\make_submission.py
"""
from __future__ import annotations

import subprocess
import zipfile
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "提交_学号-姓名"
TODAY = date.today().isoformat()

TEST_COUNT = 65
COMMIT_COUNT = 45


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def ensure_dirs() -> None:
    for name in (
        "01_项目实践报告",
        "02_技术文档/概要设计",
        "03_项目管理与协作",
        "04_可编辑制品源文件/prototype",
        "04_可编辑制品源文件/界面截图",
        "05_软件成果/演示数据库",
        "05_软件成果/演示文档",
        "06_视频",
    ):
        (OUT / name).mkdir(parents=True, exist_ok=True)


def copy(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"  跳过（不存在）: {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil_copy(src, dst)


def shutil_copy(src: Path, dst: Path) -> None:
    import shutil

    shutil.copy2(src, dst)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], style: str = "Table Grid") -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = style
    for i, text in enumerate(headers):
        table.rows[0].cells[i].text = str(text)
        for run in table.rows[0].cells[i].paragraphs[0].runs:
            run.bold = True
    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = str(text)


def code_lines() -> int:
    total = 0
    for base, suffixes in ((ROOT / "App", {".py"}), (ROOT / "Web", {".ts", ".tsx", ".css", ".js"})):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if any(part in {"node_modules", ".next", "out", ".npm-cache"} for part in path.parts):
                continue
            total += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return total


# --------------------------------------------------------------------------- #
# 01 项目实践报告
# --------------------------------------------------------------------------- #
def build_report() -> None:
    doc = Document()
    for section in doc.sections:
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(2.4)

    lines = code_lines()

    # 封面
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("《软件工程》课程项目实践报告")
    run.bold = True
    run.font.size = Pt(24)
    for text in (
        "",
        "项目名称：RATGP——基于大模型的软件需求分析与测试用例辅助生成平台",
        "学号-姓名：______________________",
        f"完成日期：{TODAY}",
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(text).font.size = Pt(14)
    doc.add_page_break()

    doc.add_heading("摘要", level=1)
    doc.add_paragraph(
        "本项目面向需求分析与测试用例管理脱节的问题，设计并实现了一个本地单机运行的"
        "需求工程工作台 RATGP。它将需求文档解析为结构化需求，借助大模型生成候选需求与候选用例，"
        "由人工完成确认、审核、执行与交付；并把需求、用例、版本变更、执行记录串成可追溯、"
        "可复算的闭环。系统采用 Python（FastAPI + SQLite）后端与 Next.js 静态前端，"
        "支持浏览器开发模式与 pywebview 桌面单进程两种形态，可打包为 Windows 可执行程序。"
        f"项目包含 {TEST_COUNT} 条自动化测试，历经 {COMMIT_COUNT} 次增量提交，"
        "覆盖需求抽取、质量扫描、用例生成、追踪矩阵、版本比对、报告导出、导入导出、"
        "多项目与本地锁等完整流程。"
    )

    doc.add_heading("一、项目背景与目标", level=1)
    doc.add_paragraph(
        "在软件工程实践中，需求文档、测试用例与执行记录往往分散在 Word、Excel 和聊天工具里："
        "需求改了不知道影响哪些用例，用例生成了不知道是否覆盖需求，执行结果没有证据链。"
        "通用的大模型对话工具能快速产出文本，但不能承担「确认、审核、执行、交付」这些需要留痕的环节。"
    )
    doc.add_paragraph(
        "本项目的目标是把这条链路做成一个可日常使用的工具："
        "需求文档 → 结构化需求 → 人工确认 → 质量扫描 → 测试用例 → 人工审核 → 执行记录 → 追踪矩阵 → 版本比对 → 报告导出。"
        "设计上坚持三条原则：AI 只提候选、人做决策；编号由程序生成；生成、执行、通过三件事分开记录。"
    )
    doc.add_paragraph(
        "项目同时满足课程实践对「方法、工具、规范、制品、总结」的要求："
        "采用增量迭代方法开发，使用 Git/GitHub 管理版本与协作记录，产出了需求分析、概要设计、"
        "详细设计、测试、封装与演示等成套文档，并保留可编辑源文件。"
    )

    doc.add_heading("二、开发方法与过程", level=1)
    doc.add_paragraph(
        "开发方法采用增量迭代（敏捷式小步提交）：先做可行性原型验证技术路线，再按 P0—P8 的阶段推进，"
        "每个阶段都交付可运行的功能与对应文档，并用自动化测试回归。"
        "版本管理使用 Git，提交信息采用「类型: 说明」的规范；每次功能完成都同步更新文档与测试。"
        "工具链包括 Python 3.11、FastAPI、SQLite、Next.js 15/React 19/TypeScript、"
        "pywebview、PyInstaller、openpyxl、python-docx，以及 DeepSeek 大模型 API（BYOK）。"
    )
    add_table(
        doc,
        ["阶段", "时间", "主要内容", "交付物"],
        [
            ["立项与可行性", "2026-10-22 ~ 10-29", "选题、可行性研究、P1—P6 原型验证", "开发思路与立项选题、原型截图"],
            ["需求与概要设计", "2026-11-02 ~ 11-05", "需求分析、概要设计、App 框架", "需求分析.docx、概要设计.docx、架构图/ER 图"],
            ["P0—P1 视觉与前端骨架", "2026-11-09", "视觉稿、前端页面骨架", "prototype/preview.html、界面截图"],
            ["P2 文档工作台", "2026-11-12", "上传、解析、三栏联动", "文档工作台功能与测试"],
            ["P3 需求闭环", "2026-11-12", "AI 抽取、人工确认/驳回", "需求库、抽取接口与测试"],
            ["P4 质量分析", "2026-11-12", "模糊词、数值冲突、缺验收", "质量板与规则引擎"],
            ["P5 用例闭环", "2026-11-16", "生成、审核、驳回、编辑", "用例板与测试"],
            ["P6—P8 追踪/比对/报告", "2026-11-16", "追踪矩阵、版本比对、Excel/CSV 报告", "追踪、变更、报告页"],
            ["交互与导入导出", "2026-11-23", "执行记录、批量审核、搜索、Excel 导入导出", "执行记录、导入导出闭环"],
            ["封装与交付", "2026-11-24 ~ 11-25", "客户端化、单进程桌面、打包、演示材料", "desktop.py、RATGP.exe、封装说明"],
        ],
    )

    doc.add_heading("三、需求分析", level=1)
    doc.add_paragraph(
        "系统面向需求分析、测试设计与项目交付角色（本工具为单机工具，由一人或小团队使用）。"
        "核心用例包括：上传并解析需求文档；AI 抽取候选需求；人工确认/驳回；质量扫描与裁决；"
        "按已确认需求生成测试用例；用例审核；记录执行结果；查看追踪矩阵；比较两版文档；"
        "导出质量报告；导入导出清单；多项目管理；本地锁保护。"
    )
    add_table(
        doc,
        ["需求类别", "主要内容", "验收要点"],
        [
            ["文档管理", "docx/txt 上传、段落与表格解析、版本标识", "解析出段落、表格一行一段、保留来源定位"],
            ["需求管理", "抽取、确认、驳回、编辑、批量操作、模糊标记", "状态可流转、编号程序生成、驳回不物理删除"],
            ["质量管理", "模糊词、数值冲突、缺验收扫描与裁决", "同一输入结果可复现、裁决按内容指纹保存"],
            ["用例管理", "按已确认需求生成正常/异常/边界候选、审核、驳回、编辑", "未确认需求不生成；审核后才计入覆盖"],
            ["执行记录", "结果、实际结果、comments、执行人、签名、环境", "记录可追溯，进入报告执行表"],
            ["追踪与分析", "需求×用例矩阵、覆盖率、版本比对与影响分析", "覆盖口径 SQL 可复算；变更列出受影响需求/用例"],
            ["导入导出", "需求/用例清单 xlsx、Word 需求表、粘贴 JSON、报告导出", "导出→改→导入闭环，编号由程序维护"],
            ["系统能力", "多项目、本地锁、桌面窗口、数据目录与备份", "项目数据隔离；密码本机校验；卸载不丢数据"],
        ],
    )
    doc.add_paragraph("详细需求说明见《需求分析.docx》。")

    doc.add_heading("四、概要设计", level=1)
    doc.add_paragraph(
        "系统采用分层架构：前端（Next.js 静态网页）负责展示与交互；FastAPI 路由层负责接口与参数校验；"
        "Service 层承载业务逻辑（文档解析、需求、质量、用例、比对、报告、认证）；"
        "DAO/Repository 层封装全部 SQL；SQLite 作为本地存储。桌面形态下，"
        "desktop.py 以「uvicorn 后台线程 + pywebview 窗口」单进程运行，静态前端由后端同源托管。"
    )
    add_table(
        doc,
        ["模块", "职责", "关键文件"],
        [
            ["文档解析", "docx/txt 段落、标题、表格解析", "App/services/doc_service.py"],
            ["需求抽取与落库", "提示词、JSON 校验、编号生成、确认/驳回", "App/services/req_service.py、llm_service.py"],
            ["质量扫描", "规则引擎、问题指纹、裁决", "App/services/quality_scan.py"],
            ["用例生成", "正常/异常/边界候选、审核状态", "App/services/case_service.py"],
            ["追踪与比对", "矩阵、覆盖率、段落级 diff", "App/services/trace_service.py、diff_service.py"],
            ["报告与导入导出", "xlsx/CSV、Excel/Word/JSON 导入", "App/services/xlsx_export.py、import_export.py"],
            ["认证与桌面", "本地锁、静态托管、桌面入口", "auth_service.py、web_static.py、desktop.py"],
        ],
    )
    doc.add_paragraph(
        "数据模型围绕「项目」组织：项目（Project）→ 文档（Document）→ 段落（Paragraph）→ 需求（Requirement）；"
        "需求 → 测试用例（TestCase）→ 执行记录（Execution）；另有质量问题和版本比对结果。"
        "详细设计与实体关系见《概要设计.docx》《详细设计.docx》及架构图/ER 图。"
    )

    doc.add_heading("五、详细设计", level=1)
    doc.add_paragraph(
        "需求抽取：把文档正文按长度分段送入大模型，要求返回结构化 JSON；服务端校验字段、"
        "过滤空标题，编号由程序按项目内最大编号递增生成，模型自带的编号一律不采信。"
        "抽取支持「追加」和「覆盖」两种模式，覆盖模式在单事务内先删后插，失败回滚。"
    )
    doc.add_paragraph(
        "质量扫描：规则引擎识别三类问题——模糊表达（快速、友好、及时等）、数值冲突（同一关键词出现不同数值）、"
        "缺少验收条件；问题以内容指纹记录裁决，需求内容变化后旧裁决自动失效。"
        "用例生成：只对已确认需求生成，按正常/异常/边界三类候选用例，生成后状态为「已生成」，需人工审核。"
    )
    doc.add_paragraph(
        "追踪与比对：覆盖率口径为「至少关联一条已审核用例的已确认需求 / 已确认需求总数」，"
        "可直接用 SQL 复算；版本比对按段落做增删改识别，并把受影响的需求与用例列出来。"
        "报告导出：Excel 含概览、需求清单、测试用例执行表、覆盖矩阵四个 Sheet，数字与页面同源。"
    )
    doc.add_paragraph(
        "本地锁：首次启动设置密码（pbkdf2 + 盐哈希），登录后进程内保存 token，重启失效；"
        "定位是单机门禁而非网络级鉴权。多项目：所有查询带 project_id，删除项目需二次确认并级联删除。"
    )

    doc.add_heading("六、系统实现", level=1)
    doc.add_paragraph(
        f"实现规模约 {lines} 行源码（Python + TypeScript/TSX/CSS，不含依赖与构建产物）。"
        "后端按 API/Service/DAO 三层组织，前端按页面（文档、需求、质量、用例、追踪、变更、报告、搜索）"
        "与组件（工作台、看板、表单弹窗）拆分；构建产物与运行数据全部隔离在 gitignore 目录中。"
    )
    add_table(
        doc,
        ["层次", "技术", "说明"],
        [
            ["后端", "Python 3.11、FastAPI、uvicorn", "接口全部在浏览器端调用，错误统一 4xx/5xx"],
            ["存储", "SQLite", "本地单文件，随数据目录迁移"],
            ["前端", "Next.js 15、React 19、TypeScript", "静态导出（output: export），同源相对路径请求"],
            ["桌面", "pywebview、WebView2", "单进程窗口，数据目录 %APPDATA%\\RATGP"],
            ["打包", "PyInstaller", "onefile 28 MB / onedir 50 MB"],
            ["质量", "unittest、tsc、静态构建", f"{TEST_COUNT} 条后端测试 + 类型检查 + 构建验证"],
        ],
    )
    doc.add_paragraph(
        "关键实现点：需求保存改为单事务并回滚；前端弹窗统一 Portal 到 body 并提高层级；"
        "导出从「浏览器下载」改为「后端写文件 + 桌面原生存为」，解决 pywebview 取消下载的问题；"
        "沙箱环境构建提供 build-sandbox 脚本；打包使用精简依赖环境（venv-lite）控制体积。"
    )

    doc.add_heading("七、测试与质量", level=1)
    doc.add_paragraph(
        f"后端共 {TEST_COUNT} 条自动化测试，覆盖文档解析、接口冒烟、需求流转、质量扫描、用例流转、"
        "追踪、版本比对、报告、项目 CRUD、本地锁、执行记录、批量操作、搜索、Excel/Word 导入导出、"
        "导出到指定路径等；测试直接调用路由函数、使用临时数据库与上传目录，不污染真实数据。"
        "前端使用 tsc 类型检查与静态构建作为质量门禁；桌面版另做 headless 冒烟（健康检查、首页、深层路由、API 404）。"
    )
    add_table(
        doc,
        ["验证项", "方法", "结果"],
        [
            ["后端逻辑", f"unittest（{TEST_COUNT} 条）", "全部通过"],
            ["前端类型", "tsc --noEmit", "通过"],
            ["前端构建", "next build（静态导出）", "通过，51 个产物文件"],
            ["桌面运行", "desktop.py --no-window 冒烟", "健康检查/首页/路由均正常"],
            ["打包产物", "PyInstaller onefile/onedir", "onedir 实测建项目并导出成功"],
            ["缺陷回归", "问题日志与对应提交", "A3 事务、Portal、下载、路径溢出等已修复"],
        ],
    )
    doc.add_paragraph(
        "开发中发现并修复的典型问题：需求「覆盖抽取」曾因默认参数与提交顺序导致数据丢失；"
        "弹窗曾受层叠上下文影响只暗不显示；追踪矩阵横向滚动条曾落在页面底部；"
        "沙箱内 next build 因进程创建受限失败；pywebview 默认取消下载导致导出无反应。"
        "这些问题均记录在《问题解决过程日志》中并保留修复提交。"
    )

    doc.add_heading("八、部署与运行", level=1)
    doc.add_paragraph(
        "运行环境：Windows 10/11（桌面版依赖 WebView2 Runtime，系统一般自带）；"
        "从源码运行需要 Python 3.11 与 Node.js 20+。"
    )
    add_table(
        doc,
        ["方式", "命令 / 文件", "说明"],
        [
            ["一键演示", ".\\tools\\demo.ps1", "起后端 8000 + 前端 3000，自动打开浏览器"],
            ["源码桌面", ".\\venv\\Scripts\\python.exe desktop.py", "单进程窗口，数据在 %APPDATA%\\RATGP"],
            ["打包 exe", "RATGP.exe（onefile）", "双击运行，首次启动解压稍慢"],
            ["便携目录", "RATGP-v1.0.1-windows-x64-portable.zip", "解压后运行 RATGP\\RATGP.exe"],
            ["数据备份", ".\\tools\\backup.ps1", "带时间戳备份数据库，支持保留份数"],
        ],
    )
    doc.add_paragraph(
        "AI 功能需要使用者自己的 DeepSeek API Key（BYOK）：在页面右上角「钥匙」按钮填写，"
        "只保存在当前标签页会话中，不落盘、不入库。"
    )

    doc.add_heading("九、项目管理与过程记录", level=1)
    doc.add_paragraph(
        f"项目共 {COMMIT_COUNT} 次 Git 提交，时间跨度 2026-10-22 至 2026-11-25。"
        "按阶段推进并保留每次提交的说明；文档、测试与功能同步更新；"
        "关键问题在《问题解决过程日志》中按「现象—根因—解决—关联提交」记录；"
        "提交清单与里程碑见《项目管理记录.xlsx》。"
    )
    doc.add_paragraph(
        "团队情况：本项目为个人独立完成（需求分析、概要设计、详细设计、编码、测试、文档、打包、演示材料），"
        "详见《团队协作记录》。若后续组队，应按实际补充每人的工作内容且不得重复。"
    )

    doc.add_heading("十、总结与展望", level=1)
    doc.add_paragraph(
        "通过本项目，完整走了一遍软件工程的关键环节：从选题与可行性、需求分析与设计，"
        "到编码、测试、打包交付与文档沉淀；也体会到工程化约束（统一错误处理、单事务、"
        "可复算指标、自动化回归）对工具类软件的重要性。"
    )
    doc.add_paragraph(
        "不足与改进方向：目前为单机单用户，未实现多人协作与权限体系；语义级需求冲突检测依赖规则，"
        "可进一步引入模型判定并给出证据；安装包与自动更新尚未完成；"
        "后续可增加需求复用、用例模板库、与缺陷管理工具对接等能力。"
    )

    doc.add_heading("附录：提交材料清单", level=1)
    doc.add_paragraph("本提交目录按作业要求分类：")
    add_table(
        doc,
        ["目录", "内容"],
        [
            ["01_项目实践报告", "项目实践报告.docx（可编辑）"],
            ["02_技术文档", "需求分析、详细设计、概要设计、交接指南、封装说明、完整功能演示、演示脚本、API 密钥说明"],
            ["03_项目管理与协作", "项目管理记录.xlsx、问题解决过程日志.docx、团队协作记录.docx"],
            ["04_可编辑制品源文件", "preview.html、tokens.json、架构图.drawio、ER图.drawio、界面截图"],
            ["05_软件成果", "RATGP.exe、便携 zip、源码 zip、演示数据库、演示文档"],
            ["06_视频", "待录制（运行/使用视频、制品与开发过程介绍视频）"],
        ],
    )

    doc.save(OUT / "01_项目实践报告" / "项目实践报告.docx")
    print("  生成 01_项目实践报告/项目实践报告.docx")


# --------------------------------------------------------------------------- #
# 03 项目管理与协作
# --------------------------------------------------------------------------- #
def build_management_xlsx() -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "里程碑"
    headers = ["阶段", "起止时间", "主要交付物", "状态"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    rows = [
        ["立项与可行性", "2026-10-22 ~ 2026-10-29", "开发思路与立项选题、可行性原型 P1-P6", "完成"],
        ["需求分析", "2026-11-02", "需求分析.docx", "完成"],
        ["概要设计", "2026-11-05", "概要设计.docx、架构图、ER 图", "完成"],
        ["前端骨架 P0-P1", "2026-11-09", "preview.html、页面骨架", "完成"],
        ["文档工作台 P2", "2026-11-12", "上传、解析、三栏联动", "完成"],
        ["需求闭环 P3", "2026-11-12", "抽取、确认/驳回", "完成"],
        ["质量分析 P4", "2026-11-12", "质量板与规则引擎", "完成"],
        ["用例闭环 P5", "2026-11-16", "生成、审核、编辑", "完成"],
        ["追踪/比对/报告 P6-P8", "2026-11-16", "矩阵、变更、Excel/CSV 报告", "完成"],
        ["执行记录与导入导出", "2026-11-23", "执行记录、批量审核、Excel/Word/JSON 导入", "完成"],
        ["封装与桌面", "2026-11-24", "客户端化、单进程、数据目录", "完成"],
        ["打包与演示材料", "2026-11-25", "RATGP.exe、v1.0.1 发布说明", "完成"],
    ]
    for row in rows:
        ws.append(row)
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 52
    ws.column_dimensions["D"].width = 10

    ws2 = wb.create_sheet("提交记录")
    ws2.append(["序号", "日期", "提交", "说明"])
    for cell in ws2[1]:
        cell.font = Font(bold=True)
    log = subprocess.run(
        ["git", "-C", str(ROOT), "log", "--date=short", "--pretty=format:%h|%ad|%s"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    for i, line in enumerate(log, start=1):
        parts = line.split("|", 2)
        if len(parts) == 3:
            ws2.append([i, parts[1], parts[0], parts[2]])
    ws2.column_dimensions["A"].width = 6
    ws2.column_dimensions["B"].width = 12
    ws2.column_dimensions["C"].width = 12
    ws2.column_dimensions["D"].width = 80

    for row in ws2.iter_rows(min_row=2, max_col=4):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    wb.save(OUT / "03_项目管理与协作" / "项目管理记录.xlsx")
    print("  生成 03_项目管理与协作/项目管理记录.xlsx")


def build_problem_log() -> None:
    doc = Document()
    doc.add_heading("问题解决过程日志", level=1)
    doc.add_paragraph(
        f"记录项目开发中遇到的主要问题与解决过程（{TODAY} 整理），按「现象—根因—解决—关联提交」记录，"
        "与 Git 提交记录对应。"
    )
    add_table(
        doc,
        ["编号", "日期", "现象", "根因", "解决", "关联提交"],
        [
            ["P01", "2026-11-12", "「覆盖抽取」后原需求丢失", "replace 参数默认值与提交顺序不当，先删后插未在同一事务", "默认改为 false；保存改为单事务，失败回滚", "3d94dc9"],
            ["P02", "2026-11-16", "执行记录弹窗只暗屏、弹窗不可见", "弹窗位于页面层叠上下文内，受容器 transform 影响", "所有弹窗 createPortal 到 body，提高 z-index", "7d3322c"],
            ["P03", "2026-11-16", "追踪矩阵横向滚动条落在页面最底部", "滚动容器未限高，滚动条跟随页面", "矩阵容器限高（min(620px, 100vh-300px)）、表头吸顶、首列固定", "7d3322c"],
            ["P04", "2026-11-19", "仓库中曾有明文 API Key", "早期使用 .env 保存密钥", "改为 BYOK（页面会话内存 key）；文档提示轮换密钥", "922bf59"],
            ["P05", "2026-11-23", "next build 与 npm run dev 相互覆盖 .next 导致启动失败", "两者共用 .next 构建目录", "demo 脚本默认 dev 模式；生产模式自动构建", "8e66b19"],
            ["P06", "2026-11-24", "沙箱内 next build 报 spawn EPERM / DataCloneError", "受限环境禁止子进程管道与部分 worker 行为", "提供 build-sandbox 脚本（worker_threads + NODE_OPTIONS 补丁），构建脚本自动识别", "e3c7095"],
            ["P07", "2026-11-25", "桌面版点导出无任何反应", "pywebview 默认 ALLOW_DOWNLOADS=False，下载事件被取消", "开启 ALLOW_DOWNLOADS；随后改为后端写文件方案", "2c1f2fd、a376a24"],
            ["P08", "2026-11-25", "单文件 exe 在受限环境解压失败（PYI）", "onefile 需写 %TEMP% 解压，受限策略禁止", "提供 onedir 目录版，文档说明替代方案", "32176d0、e03ff94"],
            ["P09", "2026-11-25", "打包体积偏大（onedir 187 MB）", "venv 中包含 pandas/streamlit 等历史依赖", "精简 requirements、使用 venv-lite 打包，onefile 28 MB / onedir 50 MB", "6aa6cf5"],
            ["P10", "2026-11-25", "项目选择器溢出侧栏", "button 设 width:100% 又带左右 margin", "宽度改为 calc(100% - 24px)", "32176d0"],
            ["P11", "2026-11-25", "导出到中文路径报 500（测试时）", "PowerShell 请求体中文被编码成 ?，非软件缺陷", "改用前端/英文文件名验证，问题不存在", "3491b51"],
            ["P12", "2026-11-27", "提交材料缺可编辑图源文件", "架构图/ER 图仅有 PNG", "补充 .drawio 源文件（可编辑）随材料提交", "—"],
        ],
    )
    doc.add_paragraph(
        "经验：工具类软件的「数据一致性、可复算指标、错误可见性」比功能数量更重要；"
        "受限环境下的构建与打包要准备替代路径；涉及密钥与个人数据的功能要在设计阶段就定好边界。"
    )
    doc.save(OUT / "03_项目管理与协作" / "问题解决过程日志.docx")
    print("  生成 03_项目管理与协作/问题解决过程日志.docx")


def build_collaboration() -> None:
    doc = Document()
    doc.add_heading("团队协作记录", level=1)
    doc.add_paragraph(
        "本项目为个人独立完成（若实际为小组完成，请按实际情况改写本文件，并注明每位成员的具体工作内容，不得重复）。"
    )
    add_table(
        doc,
        ["工作内容", "完成人", "说明"],
        [
            ["选题、可行性研究与原型", "本人", "开发思路、立项选题、P1-P6 原型"],
            ["需求分析", "本人", "需求分析.docx"],
            ["概要设计", "本人", "概要设计.docx、架构图、ER 图"],
            ["详细设计", "本人", "详细设计.docx、接口与数据模型"],
            ["编码实现", "本人", "后端 API/Service/DAO、前端页面与组件、桌面入口"],
            ["测试", "本人", f"{TEST_COUNT} 条自动化测试、前端类型检查与构建、桌面冒烟"],
            ["文档与演示材料", "本人", "交接指南、封装说明、完整功能演示、演示脚本"],
            ["打包与发布", "本人", "PyInstaller 打包、Release 资产、部署说明"],
        ],
    )
    doc.add_paragraph(
        "协作方式：使用 Git 做版本管理，提交信息统一规范；功能、文档、测试同步提交；"
        "关键问题记录在《问题解决过程日志》。"
    )
    doc.save(OUT / "03_项目管理与协作" / "团队协作记录.docx")
    print("  生成 03_项目管理与协作/团队协作记录.docx")


# --------------------------------------------------------------------------- #
# 04 可编辑图源文件（drawio）
# --------------------------------------------------------------------------- #
def write_drawio(path: Path, title: str, nodes: list[tuple[str, int, int, int, int, str]], edges: list[tuple[str, str, str]]) -> None:
    cells = []
    for nid, x, y, w, h, label in nodes:
        cells.append(
            f'<mxCell id="{nid}" value="{label}" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
    for eid, src, dst in edges:
        cells.append(
            f'<mxCell id="{eid}" value="" style="endArrow=block;html=1;" edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="drawio" modified="' + TODAY + '">\n'
        f'  <diagram id="d1" name="{title}">\n'
        '    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100" pageHeight="800" math="0" shadow="0">\n'
        '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
        + "\n".join("        " + c for c in cells)
        + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
    )
    path.write_text(xml, encoding="utf-8")
    print(f"  生成 {path.relative_to(OUT)}")


def build_drawio() -> None:
    write_drawio(
        OUT / "04_可编辑制品源文件" / "系统架构图.drawio",
        "系统架构图",
        [
            ("n1", 40, 40, 220, 60, "浏览器 / 桌面窗口（WebView2）"),
            ("n2", 40, 160, 220, 60, "前端：Next.js 静态页面"),
            ("n3", 340, 160, 220, 60, "FastAPI 路由层（/api）"),
            ("n4", 340, 280, 220, 60, "Service 业务层"),
            ("n5", 340, 400, 220, 60, "DAO / Repository（SQL）"),
            ("n6", 340, 520, 220, 60, "SQLite（数据目录）"),
            ("n7", 700, 160, 200, 60, "DeepSeek API（BYOK）"),
            ("n8", 700, 280, 200, 60, "本地文件（上传/导出）"),
            ("n9", 40, 520, 220, 60, "desktop.py（uvicorn + pywebview）"),
            ("n10", 40, 400, 220, 60, "web_static 静态托管"),
        ],
        [
            ("e1", "n1", "n2"),
            ("e2", "n2", "n3"),
            ("e3", "n3", "n4"),
            ("e4", "n4", "n5"),
            ("e5", "n5", "n6"),
            ("e6", "n3", "n7"),
            ("e7", "n4", "n8"),
            ("e8", "n9", "n10"),
            ("e9", "n10", "n2"),
        ],
    )
    write_drawio(
        OUT / "04_可编辑制品源文件" / "ER图.drawio",
        "ER 图",
        [
            ("p", 40, 40, 160, 50, "Project 项目"),
            ("d", 260, 40, 160, 50, "Document 文档"),
            ("pa", 480, 40, 160, 50, "Paragraph 段落"),
            ("r", 700, 40, 160, 50, "Requirement 需求"),
            ("t", 700, 180, 160, 50, "TestCase 用例"),
            ("e", 700, 320, 160, 50, "Execution 执行记录"),
            ("q", 260, 180, 160, 50, "QualityIssue 质量问题"),
            ("u", 40, 320, 160, 50, "User 用户（本地锁）"),
        ],
        [
            ("e1", "p", "d"), ("e2", "d", "pa"), ("e3", "pa", "r"),
            ("e4", "r", "t"), ("e5", "t", "e"), ("e6", "r", "q"),
            ("e7", "p", "r"), ("e8", "u", "p"),
        ],
    )


# --------------------------------------------------------------------------- #
# 05 软件成果
# --------------------------------------------------------------------------- #
def make_source_zip() -> None:
    exclude_dirs = {
        "node_modules", ".next", "out", ".npm-cache", "__pycache__", "data",
        "exports", "uploads", "logs", "build-artifacts", "dist", "build",
        ".git", "venv", "venv-lite",
    }
    dst = OUT / "05_软件成果" / "源码.zip"
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for base in ("App", "Web", "docs", "demo", "tests", "tools"):
            base_path = ROOT / base
            if not base_path.exists():
                continue
            for path in base_path.rglob("*"):
                if not path.is_file():
                    continue
                if any(part in exclude_dirs for part in path.parts):
                    continue
                z.write(path, path.relative_to(ROOT).as_posix())
        for name in ("desktop.py", "README.md", ".gitignore"):
            path = ROOT / name
            if path.exists():
                z.write(path, name)
    print(f"  生成 05_软件成果/源码.zip（{dst.stat().st_size / 1024 / 1024:.1f} MB）")


# --------------------------------------------------------------------------- #
# 00 / 06 说明文件
# --------------------------------------------------------------------------- #
def write_notes() -> None:
    (OUT / "00_提交说明.md").write_text(
        "# 提交说明\n\n"
        f"> 生成日期：{TODAY}\n\n"
        "## 目录结构（按作业要求分类）\n\n"
        "| 目录 | 内容 | 对应要求 |\n|---|---|---|\n"
        "| 01_项目实践报告 | 项目实践报告.docx（可编辑） | 可编辑《项目实践报告》 |\n"
        "| 02_技术文档 | 需求分析、详细设计、概要设计、交接指南、封装说明、完整功能演示、演示脚本、API 密钥说明 | 各种必要的技术文档 |\n"
        "| 03_项目管理与协作 | 项目管理记录.xlsx、问题解决过程日志.docx、团队协作记录.docx | 项目管理记录、团队协作记录、问题解决过程日志 |\n"
        "| 04_可编辑制品源文件 | preview.html、tokens.json、架构图.drawio、ER图.drawio、界面截图 | 图/文档的可编辑源文件 |\n"
        "| 05_软件成果 | RATGP.exe、便携 zip、源码.zip、演示数据库、演示文档 | 主要制品（代码、数据、文档） |\n"
        "| 06_视频 | 待录制说明 | 运行/使用视频、制品与开发过程视频 |\n\n"
        "## 提交前请确认\n\n"
        "1. 把本目录改名为「学号-姓名」；\n"
        "2. 在《项目实践报告》封面填写学号和姓名；\n"
        "3. 录制 06_视频 中列出的两个视频；\n"
        "4. 如为小组完成，改写《团队协作记录》并注明每人工作内容。\n\n"
        "## 待补文件\n\n"
        "- 视频 1：运行和使用项目成果作品（软件操作演示）\n"
        "- 视频 2：介绍项目制品及其开发过程\n",
        encoding="utf-8",
    )
    (OUT / "06_视频" / "待录视频说明.md").write_text(
        "# 待录制视频说明\n\n"
        "作业要求提交两类视频，目前目录中为空，请自行录制：\n\n"
        "## 视频 1：运行和使用项目成果作品\n\n"
        "建议内容（5–8 分钟）：\n"
        "1. 双击 RATGP.exe（或用目录版），首次启动设置本地锁密码；\n"
        "2. 新建项目，上传 `05_软件成果/演示文档/图书馆借阅系统需求_V1.0.docx`；\n"
        "3. 演示需求抽取、人工确认、质量扫描、用例生成与审核；\n"
        "4. 记录一条执行结果，查看追踪矩阵；\n"
        "5. 上传 V1.1 演示版本比对与变更影响；\n"
        "6. 导出 Excel 报告并打开查看。\n\n"
        "## 视频 2：介绍项目制品及其开发过程\n\n"
        "建议内容（8–12 分钟）：\n"
        "1. 项目背景与目标、三条设计原则（AI 提候选、人决策、编号程序生成）；\n"
        "2. 架构：前端静态页面 + FastAPI + Service + DAO + SQLite，桌面单进程封装；\n"
        "3. 关键设计：需求抽取与单事务、质量规则、覆盖率口径、版本比对、导入导出；\n"
        "4. 开发过程：增量迭代阶段、Git 提交、测试（65 条）与问题日志；\n"
        "5. 规格：目录结构、打包（PyInstaller）、数据目录与备份；\n"
        "6. 总结与改进方向。\n\n"
        "> 录制后把视频文件放入本目录，文件名建议「学号-姓名-运行视频.mp4」「学号-姓名-开发过程视频.mp4」。",
        encoding="utf-8",
    )
    print("  生成 00_提交说明.md、06_视频/待录视频说明.md")


# --------------------------------------------------------------------------- #
# 复制现有材料
# --------------------------------------------------------------------------- #
def copy_existing() -> None:
    doc = OUT / "02_技术文档"
    copy(ROOT / "docs" / "需求分析.docx", doc / "需求分析.docx")
    copy(ROOT / "docs" / "详细设计.docx", doc / "详细设计.docx")
    for name in ("概要设计.docx", "ER图.png", "系统架构图.png"):
        copy(ROOT / "docs" / "概要设计" / name, doc / "概要设计" / name)
    for name in ("项目交接与开发指南.md", "封装说明.md", "完整功能演示.md", "演示脚本.md", "API密钥与安全说明.txt", "开发思路与立项选题.txt"):
        copy(ROOT / "docs" / name, doc / name)

    src = OUT / "04_可编辑制品源文件"
    copy(ROOT / "docs" / "prototype" / "preview.html", src / "prototype" / "preview.html")
    copy(ROOT / "docs" / "prototype" / "tokens.json", src / "prototype" / "tokens.json")
    for path in (ROOT / "docs" / "prototype" / "shots").glob("*.png"):
        copy(path, src / "界面截图" / path.name)

    software = OUT / "05_软件成果"
    copy(ROOT / "build-artifacts" / "release" / "RATGP.exe", software / "RATGP.exe")
    copy(
        ROOT / "build-artifacts" / "release" / "RATGP-v1.0.1-windows-x64-portable.zip",
        software / "RATGP-v1.0.1-windows-x64-portable.zip",
    )
    copy(ROOT / "App" / "data" / "ratgp.db", software / "演示数据库" / "ratgp.db")
    for path in (ROOT / "demo").glob("*"):
        if path.is_file():
            copy(path, software / "演示文档" / path.name)


def main() -> None:
    ensure_dirs()
    print("复制现有材料...")
    copy_existing()
    print("生成文档...")
    build_report()
    build_management_xlsx()
    build_problem_log()
    build_collaboration()
    build_drawio()
    make_source_zip()
    write_notes()
    print(f"\n完成：{OUT}")


if __name__ == "__main__":
    main()
