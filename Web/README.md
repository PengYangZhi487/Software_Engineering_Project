# RATGP Web · P3（文档 + 需求闭环）

P0 是「一页静态设计稿」，P1 把它变成真的 Next.js 应用，P2 把文档工作台接上 FastAPI，P3 把**需求抽取与人工确认**接通：抽取结果进库、逐条确认/驳回、概览与侧栏数字全部来自真实数据库。

## 客户端化与静态导出（桌面封装 B 路线）

前端不再依赖 Node 服务端取数：`next build` 用 `output: "export"` 生成 `out/`，由 Python（pywebview 壳）同源托管；所有数据在浏览器里通过相对路径 `/api/...` 请求同一进程里的 FastAPI。

- `lib/data.ts`：原来的服务端 `load*` 全部改成客户端 fetch（失败时返回 `source: "mock"` + error，页面统一渲染 `<Offline />`）。
- `lib/use-api.ts`：`useApi(loader)` 提供 `loading / refreshing / error / data / reload`；写操作成功后调 `notifyDataChanged()`，所有活着的 `useApi`（含侧栏数字）一起重新取数——不再用 `router.refresh()`。
- 每个页面都是客户端组件，首屏 HTML 是骨架，浏览器拿到数据再填充。
- `app/page.tsx` 的根路径跳转改成客户端 `router.replace("/overview")`。

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

开发态默认请求 `http://127.0.0.1:8000`（`NODE_ENV=development` 时自动使用）；
生产静态导出默认用同源相对路径，见「配置」。

### 构建（静态导出）

```powershell
npm run build            # 正常环境：产出 out/
```

受限环境（DSH 沙箱 / 禁止 `child_process.fork` 的 CI）里 `next build` 的 worker 会报
`spawn EPERM`，改用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-sandbox.ps1
```

它只在该进程里切到 `worker_threads` 并注入 `scripts/sandbox-worker-patch.cjs`，产物同样是 `out/`。

Node ≥ 18；本项目在 Node 24 + Next 15.5 上验证。

## 页面

| 路由 | 内容 | 数据 |
|---|---|---|
| `/overview` | 指标条、主线 7 步、待办、最近活动、问题分布 | **后端 API** |
| `/document` | 上传（拖拽 / 版本号）、段落大纲、原文、候选需求联动 | **后端 API** |
| `/requirements` | 筛选、搜索、批量选择、抽屉、确认 / 驳回 | **后端 API** |
| `/quality` | 质量问题看板（模糊 / 冲突 / 缺验收） | **后端 API** |
| `/cases` | 用例生成（可勾选需求）、批量审核、执行记录 | **后端 API** |
| `/trace` | 需求 × 用例矩阵、覆盖率、未覆盖清单 | **后端 API** |
| `/changes` | 两版文档左右对照、受影响需求与用例 | **后端 API** |
| `/report` | 需求 / 问题 / 用例 / 覆盖率汇总，下载 Excel / CSV | **后端 API** |
| `/search` | 全局搜索：需求 / 用例 / 质量问题 | **后端 API** |

> 后端连不上时不装假数据：各页面统一渲染 `<Offline />`（带启动命令和「重试」），不会白屏。

## 文档工作台怎么接的

1. **客户端取数**：`app/(workspace)/document/page.tsx` 用 `useApi(loadDocumentWorkspace)` 在浏览器里调 `GET /api/projects/1/documents` 和 `GET /api/documents/{id}/paragraphs`，失败时渲染「后端没连上」的提示 + 启动命令，不会白屏。
2. **上传**：`components/upload-card.tsx` 走 `POST /api/projects/1/documents`（multipart），成功后 `notifyDataChanged()`，当前页与侧栏数字一起重新取数。
3. **联动**：选中的段落高亮并在三栏间联动——点左侧大纲滚动到段落，点正文段落右侧出现该段的候选需求。
4. **标题/时间**：标题取第一个 `Heading 1`，正文里不再重复；`upload_time` 是 UTC，前端统一按东八区显示。

候选需求来自真实需求表（按 `source_location.para_no` 挂到段落上），不再是本地 mock。

## P3：需求抽取与确认

- 后端 `POST /api/projects/1/requirements/extract` 会调用 DeepSeek 抽取，结果以 `未审核` 入库、编号由程序生成（`CR-001…`）。
- 前端 `/requirements` 读 `GET /api/projects/1/requirements`，抽屉里的 **确认 / 驳回 / 撤回** 直接 `PATCH /api/projects/{project_id}/requirements/{id}`，成功后 `notifyDataChanged()` 重新取数。
- 顶部与侧栏的数字（需求总数、模糊数、待审核）由同一份客户端取数得到，和列表一致。

## P4：质量分析与抽取入口

- **抽取需求**：`/document` 的按钮已点亮。已有需求时会先弹确认条，可选「追加抽取」（`replace=false`，接着当前编号续号、不删已有需求）或「覆盖并抽取」（`replace=true`，清空后重写）；项目里还没有需求时直接走追加。期间显示已等待秒数。
- **质量分析**：`/quality` 读 `GET /api/projects/1/quality/issues`，按 模糊 / 冲突 / 缺验收 筛选；每条问题可直接跳到对应需求。
- 扫描是确定性的：同一份数据每次结果一致，不调 LLM、不改数据；侧栏「质量」与概览的「待处理问题」都取自它。
- **用例**：`/cases` 按已确认需求生成（可勾选子集），生成过程显示等待秒数；每条用例可「审核通过 / 驳回 / 撤回」，三态与后端一致。
- **追踪**：`/trace` 用环形图展示覆盖率（已确认需求中被**已审核**用例覆盖的比例），矩阵里蓝色＝已关联已审核、黄色＝已关联待审核、空心＝未关联；右侧「未覆盖需求」可跳到需求抽屉。矩阵容器限高、表头吸顶、需求列固定，横向滚动条始终在容器内可见。
- **变更**：`/changes` 默认对比「次新版本 vs 最新版本」，段落级 diff 左右对照，标出数字变化（−50 +60），并把变更段落映射到需求与其用例；页面明确写出「关联影响 ≠ 实际影响」。
- **报告**：`/report` 汇总需求、问题、用例、覆盖率，可「下载 Excel」（四个 Sheet，含测试用例执行表）和「下载 CSV」；文件与页面由同一份数据生成，数字一致。
- **执行记录**：`/cases` 每条用例可「记录执行」——结果（通过 / 失败 / 阻塞）、实际结果、测试 comments、执行人、测试者签名、执行环境；卡片显示「最近执行」，顶部统计执行次数。执行不改写审核状态，覆盖率口径不受影响。
- **批量审核**：`/cases` 勾选多条用例后批量通过 / 驳回；`/requirements` 已有批量确认 / 驳回。
- **全局搜索**：顶部搜索框回车跳 `/search?q=`，一次搜需求、用例、质量问题三组结果。
- **导入 / 导出**：`/requirements` 可导出可编辑需求清单（xlsx）、导入 Excel / Word 需求表，或粘贴大模型 JSON；`/cases` 可导出用例清单、导入 Excel。导出 → Excel 里改 → 导入回来，编号由程序续。

## 结构

```
Web/
├─ app/
│  ├─ layout.tsx              # <html data-theme> + 首屏主题脚本（防闪烁）
│  ├─ page.tsx                # 根路径客户端跳转 /overview
│  ├─ globals.css             # 设计系统（tokens → 组件 → 三套主题）
│  └─ (workspace)/
│     ├─ layout.tsx           # AppShell（客户端：侧栏数字 useApi 取数）
│     ├─ overview/page.tsx
│     ├─ document/page.tsx    # useApi → DocWorkspace
│     ├─ requirements/page.tsx
│     ├─ quality/  cases/  trace/  changes/  report/  search/
├─ components/
│  ├─ sidebar.tsx  topbar.tsx  theme-menu.tsx  icon.tsx
│  ├─ api-key-dialog.tsx      # API Key 设置弹窗（BYOK）
│  ├─ change-alert.tsx        # 文档改版提醒（受影响需求 / 用例）
│  ├─ project-dialog.tsx      # 项目新建 / 重命名 / 删除
│  ├─ req-explorer.tsx        # 需求表格 + 筛选 + 抽屉
│  ├─ doc-workspace.tsx       # 三栏联动（客户端）
│  ├─ loading.tsx  offline.tsx # 首屏骨架 / 离线态
│  └─ upload-card.tsx         # 拖拽上传 + 版本号
├─ lib/
│  ├─ api.ts                  # 请求入口（apiFetch / 上传 / 导入导出 / 项目 CRUD）
│  ├─ data.ts                 # 客户端取数：需求/质量/用例/追踪/变更/报告/搜索/项目列表
│  ├─ project.ts              # 当前项目（URL ?project= > localStorage）+ 切换广播
│  ├─ use-api.ts              # useApi + notifyDataChanged（全局刷新事件）
│  └─ nav.ts  quality.ts  types.ts
├─ scripts/
│  ├─ build-sandbox.ps1       # 受限环境的 next build（产物同样是 out/）
│  └─ sandbox-worker-patch.cjs
└─ docs/shots/                # 页面截图

（P0 静态视觉稿已移到 ../docs/prototype/，不参与构建）
```

## 配置

默认不用配：

- `next dev`（前端 3000）→ 自动请求 `http://127.0.0.1:8000`；
- `next build` 静态导出（桌面壳同源托管）→ 相对路径 `/api/...`。

后端不在上面两个默认地址时，用环境变量覆盖（见 `.env.example`）：

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## 本地锁

- 第一次打开（还没设密码）会先出现「设置本地锁密码」向导（至少 4 位，输两遍）；设置后需要登录一次才能进入。
- 登录 token 只存在 **sessionStorage**：刷新保持解锁，关闭标签页/窗口后需要重新登录；顶栏的盾牌按钮「锁定」会立刻回到锁屏。
- 未设置密码时不会锁；已设置但后端进程重启后视为锁定，需要重新登录（token 只存进程内存）。
- 忘记密码：没有找回入口。停掉后端，把数据目录里 `ratgp.db` 的 `User` 表中 `username = '__local_lock__'` 的记录删掉，重启后重新设置。
- 口径：本地锁是「防止别人随手打开软件改数据」的轻量门禁——业务接口不做全局拦截、数据库文件就在本机磁盘上，不提供网络级安全。

## 与 P0 的关系

`app/globals.css` 是从 P0 设计稿抽出来的同一份 CSS；组件类名（`.card` `.btn` `.nav-item` `.table-wrap` `.doc-grid` …）与 P0 一一对应，视觉不会漂。**改样式只改变量**，三个主题自动跟着变。

## 已知取舍

- 没引 Tailwind / shadcn：这套界面是 token 驱动的，P0 的 CSS 已经是成品。需要 Dialog / Select 时再按需引入单组件。
- 没有登录体系：需求 / 用例 / 报告数据全局共享，"是否配置 Key"才是事实上的身份；用户隔离属于二期。
- 大模型 Key 走 BYOK：右上角「钥匙」按钮填入，只存 sessionStorage（刷新还在、关标签页失效），不落盘、不进代码；开发本机可用环境变量 `DEEPSEEK_API_KEY`。详见 `../docs/API密钥与安全说明.txt`。
- 多项目：侧栏项目下拉切换/新建/重命名/删除（`GET/POST /api/projects`、`PATCH/DELETE /api/projects/{id}`）；当前项目记在 URL `?project=` 与 localStorage，切换后整页重新取数。删除有子数据的项目时后端 409，弹窗二次确认后带 `force=true` 级联清理。
