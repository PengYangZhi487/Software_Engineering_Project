# RATGP · 基于大模型的软件需求分析与测试用例辅助生成平台

把需求文档转成结构化、可检查、可追踪的需求，并按已确认需求生成测试用例，
再把「需求 ↔ 用例 ↔ 变更」串成一条可复算的工程闭环。

## 目录结构

```
Software_Engineering_Project/
├─ App/                 后端与领域层
│  ├─ api/              FastAPI（8000）：文档 / 需求 / 质量 / 用例 / 追踪 / 比对 / 报告
│  ├─ dao/  services/   SQLite 访问与业务逻辑（doc / llm / req / quality / case / diff）
│  ├─ data/             数据库与上传文件（不入库）
│  └─ requirements.txt
├─ Web/                 前端（Next.js，3000）
│  ├─ app/  components/ lib/
│  └─ docs/shots/       页面截图
├─ docs/                文档与设计资料
│  ├─ 需求分析.docx  详细设计.docx  开发思路与立项选题.txt
│  ├─ 概要设计/         ER 图、架构图、概要设计文档
│  └─ prototype/        P0 静态视觉稿（preview.html + 截图）
├─ tests/               测试与数据集
│  └─ datasets/         选课系统需求说明书（25 条，含模糊/冲突）
├─ tools/               运维脚本
│  └─ seed_demo.py      清空并重建演示数据（不调用大模型）
├─ archive/             历史产物（不参与构建，见 archive/README.md）
│  ├─ streamlit-v1/     v1 Streamlit 版（已被 Web v2 取代）
│  ├─ feasibility/      可行性原型 P1–P6
│  ├─ hld-test/         早期服务层验证脚本
│  ├─ evidence/         可行性阶段截图（gitignore）
│  └─ notes/            零散笔记
├─ venv/                Python 虚拟环境
└─ .gitignore
```

## 快速启动

```powershell
# 后端（8000）
.\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000

# 前端（3000，另开终端）
cd Web
npm install      # 第一次
npm run dev
```

一键演示（答辩推荐）：

```powershell
.\tools\demo.ps1         # 默认 dev：起后端 + 前端 + 打开浏览器
.\tools\demo.ps1 -Reset  # 先重建演示数据（会清空所有项目）
.\tools\demo.ps1 -Prod   # 生产模式（缺构建时自动 next build）
```

桌面版（单进程，B 路线封装：FastAPI + 静态前端 + pywebview 窗口）：

```powershell
.\tools\build_web.ps1                      # 构建静态前端 → web_dist（沙箱里自动走 build-sandbox）
.\venv\Scripts\python.exe desktop.py       # 起窗口；数据在 %APPDATA%\RATGP
```

细节见 `docs/封装说明.md`（数据目录、备份、打包 exe）。

- 接口文档：http://127.0.0.1:8000/docs
- 前端页面：http://localhost:3000

## 配置 DeepSeek API Key

平台不内置 key（BYOK）：在页面右上角「钥匙」按钮里粘贴你自己的 DeepSeek API Key，
它只存在当前标签页的 sessionStorage 里，刷新还在、关标签页失效，不落盘。

开发者本机调试可以用环境变量，优先级低于请求头：

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."   # 只对当前终端有效
```

两者都没有时，两个调用大模型的接口会返回 401 并提示去设置。
项目不再读取 `.env`，细节见 `docs/API密钥与安全说明.txt`。

## 测试

```powershell
.\venv\Scripts\python.exe -m unittest discover -s App\api\tests -v
```

## 演示数据

演示 / 答辩前把库恢复成固定状态（不调用大模型，可重复执行）：

```powershell
.\venv\Scripts\python.exe tools\seed_demo.py --dry-run   # 先看计划
.\venv\Scripts\python.exe tools\seed_demo.py --yes       # 执行，自动备份数据库
```

重建结果：1 个项目 · 2 个版本 · 25 条需求（14 已确认 / 11 未审核）·
12 条用例（7 已审核 / 4 已生成 / 1 已驳回）· 10 条质量问题 · 覆盖率 43% · 2 处版本变更。

## 文档入口

- 需求与分析：`docs/需求分析.docx`
- 概要设计：`docs/概要设计/`
- 视觉稿说明：`docs/prototype/README.md`
- 后端接口：`App/api/README.md`
- 前端说明：`Web/README.md`
- 交接与开发指南：`docs/项目交接与开发指南.md`
