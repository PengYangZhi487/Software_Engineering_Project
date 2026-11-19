# RATGP API（P2–P3）

FastAPI 后端，跑在 **8000** 端口，前端（`Web/`，Next.js）通过 HTTP 调它。

- P2：文档上传 + 解析 + 段落
- P3：需求抽取（LLM）+ 需求列表 + 人工确认 / 驳回

## 启动

```powershell
cd C:\Users\Pyz18\Desktop\Project\Software_Engineering_Project
.\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000
```

- 文档：http://127.0.0.1:8000/docs （Swagger，可直接试）
- 健康检查：http://127.0.0.1:8000/api/health

依赖已经在 `venv` 里。换机器时：

```powershell
.\venv\Scripts\python.exe -m pip install -r App\requirements.txt
```

## API Key（BYOK）

只有两个接口真正调用大模型：`requirements/extract` 和 `cases/generate`。它们需要请求头：

```
X-DeepSeek-Key: sk-...
```

取 key 的优先级：**请求头 > 环境变量 `DEEPSEEK_API_KEY` > 401**。
项目不再读取 `App/.env`，key 不落盘；`get_client()` 用 `lru_cache(maxsize=8)`
按 key 缓存，进程重启即释放。前端在右上角「钥匙」按钮里填写。

```powershell
# 本机调试：临时设环境变量（只对当前终端有效）
$env:DEEPSEEK_API_KEY = "sk-..."
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查，顺带返回项目数 |
| GET | `/api/projects` | 项目列表（带需求条数） |
| POST | `/api/projects/{project_id}/documents` | 上传并解析文档（multipart：`file` + `version`） |
| GET | `/api/projects/{project_id}/documents` | 该项目下的文档列表 |
| GET | `/api/documents/{doc_id}` | 文档元信息 |
| GET | `/api/documents/{doc_id}/paragraphs` | 段落列表（含 `style` / `is_heading`） |
| **POST** | `/api/projects/{project_id}/requirements/extract` | **调用 LLM 从文档抽取需求**（`?doc_id=`、`?replace=`） |
| GET | `/api/projects/{project_id}/requirements` | 需求列表（`?status=未审核`） |
| **PATCH** | `/api/projects/{project_id}/requirements/{req_id}` | **确认 / 驳回 / 撤回**（body：`{"status": "已确认"}`） |
| **GET** | `/api/projects/{project_id}/quality/issues` | **质量扫描**（模糊 / 冲突 / 缺验收） |
| **POST** | `/api/projects/{project_id}/cases/generate` | **按已确认需求生成用例**（body：`req_ids`、`replace`） |
| GET | `/api/projects/{project_id}/cases` | 用例列表（按状态 / 类型统计） |
| **PATCH** | `/api/projects/{project_id}/cases/{tc_id}` | **审核 / 驳回 / 撤回**（body：`{"status": "已审核"}`） |
| **GET** | `/api/projects/{project_id}/trace` | **追踪矩阵**（需求 × 用例 + 汇总） |
| **GET** | `/api/projects/{project_id}/trace/coverage` | **覆盖率纯 SQL 复算**（并与矩阵口径交叉校验） |
| **GET** | `/api/projects/{project_id}/document-diff` | **两版文档比对 + 受影响用例**（`?base_doc_id=`、`?target_doc_id=`） |
| **GET** | `/api/projects/{project_id}/report` | **质量报告汇总**（需求 / 问题 / 用例 / 覆盖率） |
| **GET** | `/api/projects/{project_id}/report/export` | **导出 CSV**（UTF-8 BOM，`?format=csv`） |

### 上传

```powershell
# Windows PowerShell 5.1 用 curl.exe（Invoke-RestMethod -Form 要 PowerShell 7+）
curl.exe -X POST http://127.0.0.1:8000/api/projects/1/documents `
  -F "file=@tests/datasets/course_selection_v1.docx" `
  -F "version=V1.0"
```

实测：52 段、1071 字符，段落 0 是 `Heading 1`、段落 2 是 `Heading 2`。

### 抽取需求

```powershell
# 会真正调用 DeepSeek，消耗少量额度；replace=true 会先清空该项目旧需求
curl.exe -X POST "http://127.0.0.1:8000/api/projects/1/requirements/extract?replace=true"
```

返回里 `created` 是入库条数，`ambiguous` 是命中模糊词的条数，`items` 是入库后的完整列表：

```json
{
  "created": 25, "skipped": 0, "ambiguous": 6, "replaced": true, "elapsed_ms": 18234,
  "items": [{ "req_id": "CR-001", "title": "登录认证", "status": "未审核",
              "is_ambiguous": false, "acceptance": ["..."],
              "source_location": { "para_no": 3, "raw": "...", "ratio": 0.949 } }]
}
```

### 确认 / 驳回

```powershell
curl.exe -X PATCH http://127.0.0.1:8000/api/projects/1/requirements/CR-001 `
  -H "Content-Type: application/json" -d "{\"status\":\"已确认\"}"
```

`status` 只接受 `未审核` / `已确认` / `已驳回`，其它值返回 422。

### 质量扫描（P4）

```powershell
curl.exe "http://127.0.0.1:8000/api/projects/1/quality/issues"
```

扫描是**确定性**的（同一份数据每次结果一致、不调 LLM、不改数据），因此直接 GET 即可。当前规则：

| 规则 | 判定方式 | 样例 |
|---|---|---|
| 模糊表达 | 词表命中（快速/及时/稳定…） | CR-015「快速、明显」 |
| 缺验收条件 | acceptance 为空 | — |
| 数值口径冲突 | 同主题取最小数字，跨需求不一致 | 6 门 vs 8 门；50 人 vs 100 人；2 周 vs 4 周 |
| 相反表述冲突 | 同主题同时出现「不可/不得」与「可/允许」 | 成绩不可改 vs 7 天内可改 |

实测数据集：`total=10`（模糊 6 + 冲突 4）。语义层面的复杂冲突仍由人判断，见 P4.1。

### 用例生成与审核（P5）

```powershell
# 为全部已确认需求生成（会覆盖这些需求的旧用例）
curl.exe -X POST http://127.0.0.1:8000/api/projects/1/cases/generate `
  -H "Content-Type: application/json" `
  -d "{\"replace\":true}"

# 只给勾选的两条需求生成
curl.exe -X POST http://127.0.0.1:8000/api/projects/1/cases/generate `
  -H "Content-Type: application/json" `
  -d "{\"req_ids\":[\"CR-006\",\"CR-008\"],\"replace\":true}"

# 审核 / 驳回 / 撤回
curl.exe -X PATCH http://127.0.0.1:8000/api/projects/1/cases/1 `
  -H "Content-Type: application/json" -d "{\"status\":\"已审核\"}"
```

约定：

- 只接受 `已确认` 需求；不传 `req_ids` 就为全部已确认需求生成，传了就只做子集；
- 模型只提候选，**编号与引用由程序校验**：引用了不存在需求的用例会被丢弃（写库时外键再兜一层，失败计入 `skipped`）；
- 生成结果状态为 `已生成`，审核由人做；
- `status` 只接受 `已生成` / `已审核` / `已驳回`。

### 追踪矩阵与覆盖率（P6）

```powershell
curl.exe "http://127.0.0.1:8000/api/projects/1/trace"
curl.exe "http://127.0.0.1:8000/api/projects/1/trace/coverage"
```

覆盖率口径（写死在 `routers/trace.py`，页面与报告共用）：

```
分子 = 至少关联一条「已审核」用例的已确认需求数
分母 = 已确认需求总数
```

`已生成未审核` 的用例计入矩阵（黄色格子），但**不计入分子**——避免把机器生成当成已覆盖。`/trace/coverage` 用一条 SQL 独立复算，并和矩阵口径交叉校验，返回 `consistent: true/false`，满足 G4「页面数字可独立复算」。

### 版本比对与影响（P7）

```powershell
# 默认 target = 最新文档、base = 次新文档
curl.exe "http://127.0.0.1:8000/api/projects/1/document-diff"
```

- 段落级精确比对（`difflib.SequenceMatcher`），输出 `changed / added / removed` 三类；
- 变更段落按 `source_location.para_no` 映射到需求，再查这些需求下的用例；
- 返回里区分 `removed_numbers` / `added_numbers`，前端直接标出「−50 +60」；
- **关联影响 ≠ 实际影响**：接口只列出关联用例，是否需要改由人复核；
- 少于两版文档时返回 400，前端给「上传新版本」的引导。

> 早期需求没有 `doc_id`（直接灌库），比对时按「属于旧版本」处理；重新抽取过的需求会带 `doc_id`。

### 质量报告与导出（P8）

```powershell
curl.exe "http://127.0.0.1:8000/api/projects/1/report"
curl.exe -o report.csv "http://127.0.0.1:8000/api/projects/1/report/export?format=csv"
```

- `/report` 返回项目信息、文档列表、需求/问题/用例/覆盖率汇总；
- `/report/export` 返回一个 CSV（UTF-8 BOM），包含四段：**汇总 / 需求清单 / 质量问题 / 测试用例**；
- 页面与 CSV 都由同一个 `_build()` 生成，覆盖率复用追踪模块口径 —— 导出数字和页面一致，这也是 G4 的要求；
- 目前只支持 CSV，XLSX 留到 P8.1。

## 设计约定

1. **AI 提候选，人做决策**：抽取结果一律以 `未审核` 入库，不会自动确认；用例同理，生成 ≠ 通过。
2. **编号由程序生成，项目内唯一**：`Requirement.id` 是数据库自增主键，`req_id`（`CR-001…`）只保证 `UNIQUE(project_id, req_id)`——两个项目可以各自有 `CR-001`。编号不采信模型自己编的，`replace=false` 时从本项目最大号续号。
3. **失败即清理**：上传解析失败、入库失败、超限都会删掉落盘文件；抽取/生成失败返回 502，不写库。
4. **可回退**：驳回不物理删除，状态置为 `已驳回`，便于追溯（前端可按状态筛选）。
5. **关联留痕**：每生成一条用例就写一条 `RequirementTestLink`，P6 的追踪矩阵直接用它。

## 错误码

| 码 | 场景 |
|---|---|
| 400 | 空文件、解析失败、没有可解析文本、项目无文档却要抽取、文档不属于该项目、docx 解压体积异常 |
| 401 | 调大模型的接口缺少 API Key（请求头和环境变量都没有） |
| 404 | 项目 / 文档 / 需求不存在 |
| 413 | 超过 10 MB |
| 415 | 扩展名不是 `.docx` / `.txt` |
| 422 | 非法状态值 |
| 502 | LLM 抽取失败（Key / 网络 / 配额） |
| 500 | 落盘或入库失败 |

## 测试

```powershell
.\venv\Scripts\python.exe -m unittest discover -s App\api\tests -v
```

22 条：段落与样式、非法扩展名、路由注册、上传→回读（含 file_path 不外露）、404/415/400、缺 Key 401、抽取→确认→驳回、两个项目可各自 CR-001、跨项目文档抽取拒绝、zip bomb 拒绝、质量规则、用例生成→审核→驳回、矩阵覆盖率与 SQL 复算一致性、两版文档比对与受影响用例、报告与 CSV 一致性（全部用假 LLM，不耗额度）。

## 下一步

MVP 主线（P2–P8）已经闭环。后续可选：

- P8.1：XLSX 多 sheet 导出、报告模板
- P9：演示脚本、录屏、答辩材料；把 Streamlit 版归档
- 二期：语义冲突检测、多项目/登录、真实测试执行
