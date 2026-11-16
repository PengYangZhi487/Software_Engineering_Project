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

- 接口文档：http://127.0.0.1:8000/docs
- 前端页面：http://localhost:3000

## 测试

```powershell
.\venv\Scripts\python.exe -m unittest discover -s App\api\tests -v
```

## 文档入口

- 需求与分析：`docs/需求分析.docx`
- 概要设计：`docs/概要设计/`
- 视觉稿说明：`docs/prototype/README.md`
- 后端接口：`App/api/README.md`
- 前端说明：`Web/README.md`
