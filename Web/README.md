# RATGP Web · P1 前端骨架

P0 是「一页静态设计稿」，P1 把它变成**真的 Next.js 应用**：路由、组件、主题、抽屉都能跑，数据还是 mock。

## 运行

```bash
cd Web
npm install
npm run dev     # http://localhost:3000 → 自动跳到 /overview
```

Node ≥ 18；本项目在 Node 24 + Next 15.1 上验证。

## 这一版做了什么

| 项 | 状态 |
|---|---|
| AppShell（侧栏 + 顶栏 + 内容区，三栏布局与 P0 一致） | ✅ |
| `/overview` 总览（指标条、主线 7 步、待办、活动、问题分布） | ✅ |
| `/requirements` 需求库（筛选、搜索、批量选择、详情抽屉） | ✅ |
| 主题：浅色（默认）/ 玻璃淡紫 / 深色，右上角切换并持久化 | ✅ |
| `/document`、`/quality`、`/cases`、`/trace`、`/changes`、`/report` | 空状态占位，按 P2–P8 逐个接 |
| 顶部搜索 `/` 快捷键、`Enter` 跳 `/requirements?q=` | ✅ |
| 需求详情抽屉：模糊词命中、冲突提示、来源段落、验收条件 | ✅ |

## 结构

```
Web/
├─ app/
│  ├─ layout.tsx              # <html data-theme> + 首屏主题脚本（防闪烁）
│  ├─ globals.css             # P0 的设计系统 1:1 迁移（tokens → 组件 → 三套主题）
│  ├─ page.tsx                # / → /overview
│  └─ (workspace)/
│     ├─ layout.tsx           # AppShell
│     ├─ overview/page.tsx
│     ├─ requirements/page.tsx
│     └─ [step]/page.tsx      # 其余步骤的空状态
├─ components/
│  ├─ sidebar.tsx  topbar.tsx  theme-menu.tsx  icon.tsx
│  └─ req-explorer.tsx        # 需求表格 + 筛选 + 抽屉（客户端组件）
├─ lib/
│  ├─ data.ts                 # mock：25 条需求 + 13 条示例用例
│  ├─ stats.ts  nav.ts  quality.ts  types.ts
├─ prototype/                 # P0 静态视觉稿（保留作对照，不参与构建）
└─ docs/shots/                # P1 页面截图
```

## 数据从哪来

- **真实**：25 条需求（CR-001～CR-025）来自 `../App/data/ratgp.db`，含验收条件、来源段落号、相似度；模糊词判定沿用 `App/services/quality_service.py` 的同一套词表，在 `lib/quality.ts` 复刻了一份。
- **示例**：13 条用例、60% 覆盖率、最近活动时间线 —— `case_service` / `track_service` 还没实现（M4–M7）。

## 与 P0 的关系

`app/globals.css` 不是重写的，是从 P0 设计稿抽出来的同一份 CSS；组件类名（`.card` `.btn` `.nav-item` `.table-wrap` `.drawer` …）与 P0 一一对应，所以视觉不会漂。**改样式只改 `globals.css` 里的变量**，三个主题自动跟着变。

## 后端（P2）

FastAPI 在 `../App/api`，端口 8000：

```powershell
cd ..
.\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000
# 文档：http://127.0.0.1:8000/docs
```

P1 的页面目前**不依赖**这个服务（走 mock）；P2 的文档工作台会接
`POST /api/projects/1/documents`（上传解析）和 `GET /api/documents/{id}/paragraphs`（段落）。

## 已知取舍

- 没引 Tailwind / shadcn：这套界面是 token 驱动的，P0 的 CSS 已经是成品；再加一层工具类收益不大。如果你希望 P2 之后用 shadcn 的 Dialog / Select，也可以只把那几个组件按需引入。
- 需求状态（确认/驳回）目前只弹提示，不改数据 —— P3 接 `App/services/req_service.py` 的 `update_status`。
- 没有登录。`auth_service.py` 还是空文件，P3 再补。
