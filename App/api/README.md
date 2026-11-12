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
| **PATCH** | `/api/requirements/{req_id}` | **确认 / 驳回 / 撤回**（body：`{"status": "已确认"}`） |
| **GET** | `/api/projects/{project_id}/quality/issues` | **质量扫描**（模糊 / 冲突 / 缺验收） |

### 上传

```powershell
# Windows PowerShell 5.1 用 curl.exe（Invoke-RestMethod -Form 要 PowerShell 7+）
curl.exe -X POST http://127.0.0.1:8000/api/projects/1/documents `
  -F "file=@test_file/datasets/course_selection_v1.docx" `
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
curl.exe -X PATCH http://127.0.0.1:8000/api/requirements/CR-001 `
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

## 设计约定

1. **AI 提候选，人做决策**：抽取结果一律以 `未审核` 入库，不会自动确认。
2. **编号由程序生成**：`CR-001…` 按顺序分配，不采信模型自己编的编号；`replace=false` 时从现有最大号续号。
3. **失败即清理**：上传解析失败、入库失败、超限都会删掉落盘文件；抽取失败返回 502，不写库。
4. **可回退**：驳回不物理删除，状态置为 `已驳回`，便于追溯（前端可按状态筛选）。

## 错误码

| 码 | 场景 |
|---|---|
| 400 | 空文件、解析失败、没有可解析文本、项目无文档却要抽取 |
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

9 条：段落与样式、非法扩展名、路由注册、上传→回读、404/415/400、抽取→确认→驳回全流程（用假 LLM，不耗额度）、空项目抽取报 400。

## 下一步（P5）

- `POST /api/projects/{id}/cases/generate`：按已确认需求生成正常 / 异常 / 边界用例
- `PATCH /api/cases/{id}`：审核状态
- 前端 `/cases` 页做候选用例审核
