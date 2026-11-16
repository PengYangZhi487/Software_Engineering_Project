# archive/ · 历史产物（不参与当前构建）

这里的文件都已被 `Web/` + `App/api/` 取代，保留是为了对照与追溯，不参与构建、不被应用引用。

| 目录 | 内容 | 说明 |
|---|---|---|
| `streamlit-v1/` | v1 Streamlit 版（app.py、pages/、ui_theme.py、操作文档.txt） | 已被 Next.js 版取代。仍可运行：`streamlit run archive/streamlit-v1/app.py` |
| `feasibility/` | 可行性原型 P1–P6（脚本 + mock 文档 + 早期 test.db） | 早期的技术验证，和现在的数据集/接口无关 |
| `hld-test/` | 早期服务层验证脚本 | 手工跑的服务层检查，已被 `App/api/tests` 的 18 条单测取代 |
| `evidence/` | 可行性阶段截图 | 过程证据，已在 .gitignore 中忽略 |
| `notes/` | 零散笔记 | 非软件产物 |

> 这些文件不要被 `App/` 或 `Web/` 引用；如需恢复某个功能，请从对应 commit 里取，
> 而不是直接把 archive 里的代码接回主线。
