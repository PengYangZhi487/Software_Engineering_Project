# RATGP Web · P3（文档 + 需求闭环）

P0 是「一页静态设计稿」，P1 把它变成真的 Next.js 应用，P2 把文档工作台接上 FastAPI，P3 把**需求抽取与人工确认**接通：抽取结果进库、逐条确认/驳回、概览与侧栏数字全部来自真实数据库。

## 运行（两个终端）

```powershell
# 终端 1：后端（8000）
cd ..
.\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000

# 终端 2：前端（3000）
cd Web
npm install      # 第一次
npm run dev
```

打开 http://localhost:3000 → 自动跳 `/overview`，侧栏「02 文档」进工作台。

Node ≥ 18；本项目在 Node 24 + Next 15.5 上验证。

## 页面

| 路由 | 内容 | 数据 |
|---|---|---|
| `/overview` | 指标条、主线 7 步、待办、最近活动、问题分布 | **后端 API** |
| `/document` | 上传（拖拽 / 版本号）、段落大纲、原文、候选需求联动 | **后端 API** |
| `/requirements` | 筛选、搜索、批量选择、抽屉、确认 / 驳回 | **后端 API** |
| `/quality` | 质量问题看板（模糊 / 冲突 / 缺验收） | **后端 API** |
| `/cases` | 用例生成（可勾选需求）、三态审核 | **后端 API** |
| `/trace` | 需求 × 用例矩阵、覆盖率、未覆盖清单 | **后端 API** |
| `/changes` | 两版文档左右对照、受影响需求与用例 | **后端 API** |
| `/report` | 需求 / 问题 / 用例 / 覆盖率汇总，下载 CSV | **后端 API** |

> 后端连不上时会自动退回 `lib/data.ts` 的示例数据，并在页面标题旁标「示例数据」，不会白屏。

## 文档工作台怎么接的

1. **服务端取数**：`app/(workspace)/document/page.tsx` 直接调 `GET /api/projects/1/documents` 和 `GET /api/documents/{id}/paragraphs`（`cache: "no-store"`），失败时渲染「后端没连上」的提示 + 启动命令，不会白屏。
2. **上传**：`components/upload-card.tsx` 走 `POST /api/projects/1/documents`（multipart），成功后 `router.refresh()` 让服务端重新取数。
3. **联动**：选中的段落高亮并在三栏间联动——点左侧大纲滚动到段落，点正文段落右侧出现该段的候选需求。
4. **标题/时间**：标题取第一个 `Heading 1`，正文里不再重复；`upload_time` 是 UTC，前端统一按东八区显示。

候选需求来自真实需求表（按 `source_location.para_no` 挂到段落上），不再是本地 mock。

## P3：需求抽取与确认

- 后端 `POST /api/projects/1/requirements/extract` 会调用 DeepSeek 抽取，结果以 `未审核` 入库、编号由程序生成（`CR-001…`）。
- 前端 `/requirements` 读 `GET /api/projects/1/requirements`，抽屉里的 **确认 / 驳回 / 撤回** 直接 `PATCH /api/projects/{project_id}/requirements/{id}`，成功后 `router.refresh()`。
- 顶部与侧栏的数字（需求总数、模糊数、待审核）都来自同一次服务端取数，和列表一致。

## P4：质量分析与抽取入口

- **抽取需求**：`/document` 的按钮已点亮。已有需求时会先弹确认条（会覆盖 N 条，含已确认的），确认后调 `POST .../requirements/extract?replace=true`，期间显示已等待秒数。
- **质量分析**：`/quality` 读 `GET /api/projects/1/quality/issues`，按 模糊 / 冲突 / 缺验收 筛选；每条问题可直接跳到对应需求。
- 扫描是确定性的：同一份数据每次结果一致，不调 LLM、不改数据；侧栏「质量」与概览的「待处理问题」都取自它。
- **用例**：`/cases` 按已确认需求生成（可勾选子集），生成过程显示等待秒数；每条用例可「审核通过 / 驳回 / 撤回」，三态与后端一致。
- **追踪**：`/trace` 用环形图展示覆盖率（已确认需求中被**已审核**用例覆盖的比例），矩阵里蓝色＝已关联已审核、黄色＝已关联待审核、空心＝未关联；右侧「未覆盖需求」可跳到需求抽屉。
- **变更**：`/changes` 默认对比「次新版本 vs 最新版本」，段落级 diff 左右对照，标出数字变化（−50 +60），并把变更段落映射到需求与其用例；页面明确写出「关联影响 ≠ 实际影响」。
- **报告**：`/report` 汇总需求、问题、用例、覆盖率，右下角「下载 CSV」直接拉后端导出的文件；文件与页面由同一份数据生成，数字一致。

## 结构

```
Web/
├─ app/
│  ├─ layout.tsx              # <html data-theme> + 首屏主题脚本（防闪烁）
│  ├─ globals.css             # 设计系统（tokens → 组件 → 三套主题）
│  └─ (workspace)/
│     ├─ layout.tsx           # AppShell
│     ├─ overview/page.tsx
│     ├─ document/page.tsx    # 服务端取数 → DocWorkspace
│     ├─ requirements/page.tsx
│     ├─ quality/  cases/  trace/  changes/  report/
│     └─ [step]/page.tsx      # 遗留空状态页（STEPS 已空，访问即 404）
├─ components/
│  ├─ sidebar.tsx  topbar.tsx  theme-menu.tsx  icon.tsx
│  ├─ api-key-dialog.tsx      # API Key 设置弹窗（BYOK）
│  ├─ req-explorer.tsx        # 需求表格 + 筛选 + 抽屉
│  ├─ doc-workspace.tsx       # 三栏联动（客户端）
│  └─ upload-card.tsx         # 拖拽上传 + 版本号
├─ lib/
│  ├─ api.ts                  # 后端唯一入口（list/paragraphs/upload）
│  ├─ data.ts                 # mock：25 条需求 + 13 条示例用例
│  └─ stats.ts  nav.ts  quality.ts  types.ts
└─ docs/shots/                # 页面截图

（P0 静态视觉稿已移到 ../docs/prototype/，不参与构建）
```

## 配置

默认就指向 `http://127.0.0.1:8000`。换地址时在 `Web/.env.local` 里写（见 `.env.example`）：

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## 与 P0 的关系

`app/globals.css` 是从 P0 设计稿抽出来的同一份 CSS；组件类名（`.card` `.btn` `.nav-item` `.table-wrap` `.doc-grid` …）与 P0 一一对应，视觉不会漂。**改样式只改变量**，三个主题自动跟着变。

## 已知取舍

- 没引 Tailwind / shadcn：这套界面是 token 驱动的，P0 的 CSS 已经是成品。需要 Dialog / Select 时再按需引入单组件。
- 没有登录体系：需求 / 用例 / 报告数据全局共享，"是否配置 Key"才是事实上的身份；用户隔离属于二期。
- 大模型 Key 走 BYOK：右上角「钥匙」按钮填入，只存 sessionStorage（刷新还在、关标签页失效），不落盘、不进代码；开发本机可用环境变量 `DEEPSEEK_API_KEY`。详见 `../docs/API密钥与安全说明.txt`。
- 多项目切换未做，前端 `projectId` 固定为 1。
