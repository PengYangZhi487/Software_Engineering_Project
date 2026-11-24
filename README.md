# RATGP · 基于大模型的软件需求分析与测试用例辅助生成平台

把需求文档转成结构化、可检查、可追踪的需求，按已确认需求生成测试用例，
再把「需求 ↔ 用例 ↔ 变更 ↔ 执行」串成一条可复算的工程闭环。

三条设计原则：**AI 只提候选、人做决策**；**编号由程序生成**；**生成 ≠ 执行 ≠ 通过**。

---

## 一、前置要求

| 项 | 版本 / 说明 |
|---|---|
| 操作系统 | Windows 10 / 11（桌面窗口依赖 WebView2 Runtime，Win10/11 一般自带） |
| Python | 3.11（项目用 `venv\Scripts\python.exe`） |
| Node.js | 20+（前端构建；npm 自带） |
| DeepSeek API Key | 抽取需求 / 生成用例时需要（BYOK，不内置） |

## 二、从头开始：把软件跑起来

### 步骤 1：安装后端依赖

```powershell
cd Software_Engineering_Project

# 第一次：创建虚拟环境（仓库里的 venv 不进 git，需要的话自己建）
python -m venv venv

# 安装依赖（含桌面版需要的 pywebview；pyinstaller 是打包时用的）
.\venv\Scripts\python.exe -m pip install -r App\requirements.txt
```

### 步骤 2：安装前端依赖

```powershell
cd Web
npm install
cd ..
```

### 步骤 3：启动

**方式 A：一键启动（推荐）**

```powershell
.\tools\demo.ps1
```

它会启动后端（8000）+ 前端（3000），等就绪后打开浏览器，并提示两个窗口不要关。

**方式 B：手动两个终端**

```powershell
# 终端 1：后端
.\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000

# 终端 2：前端
cd Web
npm run dev
```

浏览器打开 http://localhost:3000 ，接口文档在 http://127.0.0.1:8000/docs 。

### 步骤 4：配置 DeepSeek API Key

平台不内置 key（BYOK）。点页面右上角「钥匙」按钮，粘贴你自己的 DeepSeek API Key：

- 只存在当前标签页的 `sessionStorage`：刷新还在，关标签页失效，不落盘；
- 开发者本机也可以设环境变量（优先级低于页面里的 key）：
  ```powershell
  $env:DEEPSEEK_API_KEY = "sk-..."
  ```
- 两者都没有时，抽取 / 生成用例会返回 401 并提示去设置。

### 步骤 5：走一遍主线（第一次使用）

1. **上传文档**：`/document` → 「上传文档」，选 `.docx` / `.txt`，填版本号（如 `V1.0`）；
2. **抽取需求**：点「抽取需求」→ 选「追加抽取」（不删已有）或「覆盖并抽取」（清空重来）；
3. **人工确认**：`/requirements` 里逐条「确认 / 驳回」，可以勾选批量确认；
4. **质量扫描**：`/quality` 看模糊词、数值冲突、缺验收条件，逐条确认或忽略；
5. **生成用例**：`/cases` → 「生成用例」，勾选已确认需求（正常 / 异常 / 边界）；
6. **审核用例**：逐条「审核通过 / 驳回」，也可勾选批量审核；
7. **记录执行**：每条用例「记录执行」→ 填结果、实际结果、comments、执行人、签名；
8. **看追踪**：`/trace` 看需求 × 用例矩阵和覆盖率；
9. **版本比对**：上传 `V1.1` 后，`/changes` 看改版影响，文档页/总览会弹变更提醒；
10. **出报告**：`/report` 下载 Excel（含测试用例执行表）或 CSV。

### 步骤 6：导入 / 导出（Excel 当编辑器）

- `/requirements`：「导出」下载可编辑的需求清单；「导入」支持 `.xlsx` / `.docx` 需求表，或直接粘贴大模型输出的 JSON（模型编的编号会被忽略，由程序续号）；
- `/cases`：「导出」用例清单；「导入」Excel 用例表（关联需求必须存在）；
- 典型用法：导出 → 在 Excel 里批量改 → 导入回来，软件负责编号、状态、追溯；
- 桌面版点「导出」会把文件保存到数据目录的 `exports\`（默认 `%APPDATA%\RATGP\exports`），并在页面上显示完整路径；浏览器模式直接下载到下载目录。

### 步骤 7：多项目

侧栏顶部是项目选择器：可以**新建 / 重命名 / 删除**项目。删除有数据的项目会先提示，确认后才连同需求、文档、用例、执行记录一起删。切换项目后全站数据跟着切。

### 步骤 8：本地锁（可选）

首次打开会引导设置密码（至少 4 位）；之后每次打开需要解锁，顶栏盾牌按钮可以手动「锁定」。
这是本地单机门禁，防的是别人随手打开改数据；业务接口不做网络级鉴权，数据库就在本机。

### 步骤 9：桌面版（单进程窗口，不用浏览器）

```powershell
# 1) 构建静态前端（输出到 build-artifacts/web_dist）
.\tools\build_web.ps1

# 2) 起桌面窗口（FastAPI + pywebview 单进程，随机端口）
.\venv\Scripts\python.exe desktop.py
```

- 数据目录：`%APPDATA%\RATGP`（首次运行自动创建空库、uploads、backups、logs）；
- 想把现有数据带进桌面版：
  ```powershell
  New-Item -ItemType Directory -Force "$env:APPDATA\RATGP"
  Copy-Item App\data\ratgp.db "$env:APPDATA\RATGP\ratgp.db"
  ```
- 便携用法：`--no-window` 只起服务不开窗；`--port` / `--data-dir` 可覆盖默认；
- 打包 exe（可选）：先装 `pyinstaller`，再 `.\tools\build_exe.ps1`，产物在 `build-artifacts/dist/`。

### 步骤 10：备份 / 恢复

```powershell
# 桌面版数据（默认 %APPDATA%\RATGP）：备份到 %APPDATA%\RATGP\backups\
.\tools\backup.ps1

# 开发/浏览器模式数据（项目内 App\data）：显式指定库和输出目录
.\tools\backup.ps1 -DbPath .\App\data\ratgp.db -OutDir .\App\data\backups

# 只保留最近 10 份
.\tools\backup.ps1 -Keep 10
```

恢复：关掉软件，把备份文件复制回对应的 `ratgp.db`（开发模式 `App\data\ratgp.db`，桌面版 `%APPDATA%\RATGP\ratgp.db`）。

---

## 三、常用命令

```powershell
# 测试（60 条，不调大模型）
.\venv\Scripts\python.exe -m unittest discover -s App\api\tests -v

# 重建演示数据（会清空所有项目；自动备份）
.\venv\Scripts\python.exe tools\seed_demo.py --dry-run
.\venv\Scripts\python.exe tools\seed_demo.py --yes

# 一键演示
.\tools\demo.ps1          # 默认 dev
.\tools\demo.ps1 -Reset   # 先重建演示数据
.\tools\demo.ps1 -Prod    # 生产模式（缺构建时自动 next build）

# 前端类型检查 / 构建
cd Web
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
.\node_modules\.bin\next.cmd build
```

演示数据基准：1 个项目 · 2 个版本 · 25 条需求（14 已确认 / 11 未审核）·
12 条用例（7 已审核 / 4 已生成 / 1 已驳回）· 10 条质量问题 · 覆盖率 43% · 2 处版本变更。

## 四、数据与安全

- 数据库：`App\data\ratgp.db`（开发/浏览器模式）或 `%APPDATA%\RATGP\ratgp.db`（桌面版）；
- 上传原文件：对应数据目录下的 `uploads/`；
- API Key 只存在浏览器会话或环境变量，不写库、不进日志；
- 细节见 `docs/API密钥与安全说明.txt`。

## 五、常见问题

| 现象 | 处理 |
|---|---|
| 端口 3000 / 8000 被占用 | 先关掉旧的后端/前端窗口；`demo.ps1` 会明确提示端口冲突 |
| 页面提示「后端没有连上」 | 确认 FastAPI 已启动；刷新页面 |
| 抽取/生成提示 401 | 右上角钥匙按钮填 DeepSeek Key，或设 `DEEPSEEK_API_KEY` 环境变量 |
| `next build` 报 `__webpack_modules__...` | `next build` 和 `npm run dev` 不能共用 `.next`，先停 dev 再 build |
| 受限环境（DSH 沙箱）build 报 EPERM | 用 `Web\scripts\build-sandbox.ps1`；`build_web.ps1` 会自动识别 |
| onefile exe 报 `PYI: Failed to create parent directory structure` | 受限环境解压不了，改用 `-OneDir` 目录版，或在真实桌面双击 |
| 桌面版打开是空库 | 桌面版数据目录是 `%APPDATA%\RATGP`，按步骤 9 把 `App\data\ratgp.db` 复制过去 |
| 桌面版点导出没反应 | 更新到最新 exe：导出会把文件保存到数据目录的 `exports\`，页面显示完整路径；旧版才依赖浏览器下载 |

## 六、目录结构

```
Software_Engineering_Project/
├─ App/                 后端与领域层
│  ├─ api/              FastAPI：文档 / 需求 / 质量 / 用例 / 执行 / 追踪 / 比对 / 报告 / 导入导出 / 本地锁
│  ├─ dao/  services/   SQLite 访问与业务逻辑
│  ├─ data/             数据库与上传文件（不入库）
│  └─ requirements.txt
├─ Web/                 前端（Next.js，静态导出）
├─ docs/                文档与设计资料（含封装说明、交接指南、演示脚本）
├─ tests/               测试与数据集
├─ demo/                演示文档（需求 V1.0/V1.1 + Excel 导入示例）
├─ tools/               运维与构建脚本（demo / build_web / build_exe / backup / seed_demo）
├─ archive/             历史产物（不参与构建）
├─ build-artifacts/     构建产物（dist / build / web_dist / spec，gitignore）
├─ desktop.py           桌面入口（FastAPI + pywebview 单进程）
├─ venv/                开发用 Python 环境
├─ venv-lite/           精简打包环境（可选，gitignore）
└─ .gitignore
```

## 七、文档入口

- 需求与分析：`docs/需求分析.docx`
- 详细设计：`docs/详细设计.docx`
- 概要设计：`docs/概要设计/`
- **封装说明**（桌面版构建 / 数据目录 / 备份 / 打包）：`docs/封装说明.md`
- **交接与开发指南**：`docs/项目交接与开发指南.md`
- **完整功能演示（从新建项目到导出）**：`docs/完整功能演示.md`
- **答辩演示脚本**：`docs/演示脚本.md`
- 后端接口：`App/api/README.md`
- 前端说明：`Web/README.md`
- 视觉稿说明：`docs/prototype/README.md`
