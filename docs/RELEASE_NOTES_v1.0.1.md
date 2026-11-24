# RATGP v1.0.1 发布说明

> 相比 v1.0.0 的修复与改进。功能范围不变：需求抽取、确认、质量扫描、用例生成/审核、执行记录、追踪矩阵、版本比对、报告导出、导入导出、多项目、本地锁、桌面版。

## 修复

- **桌面版「导出」无反应**：pywebview 默认禁止下载，`<a download>` 会被直接取消。现在导出统一走后端接口：
  - 桌面版点「导出」会弹出 Windows 原生「另存为」对话框，可自选保存目录和文件名；
  - 浏览器模式保存到后端的 `exports/`（`App\data\exports`），页面显示完整路径；
- 导出接口新增 `target_path` 参数（带目录校验），并补充 2 条测试。

## 改进

- 演示材料：新增「图书馆借阅系统」V1.0/V1.1 演示文档（普通需求分析文档风格，含两张表格）与 `docs/完整功能演示.md` 操作手册；
- 项目目录整理：构建产物统一到 `build-artifacts/`（dist / build / web_dist / spec），根目录更清爽；
- 打包依赖精简：requirements 移除不再使用的 streamlit / pandas / python-dotenv，onefile 28.1 MB、onedir 50.5 MB；
- 桌面版导出后页面显示保存路径，并支持「复制路径」。

## 资产

| 文件 | 说明 |
|---|---|
| `RATGP.exe` | 单文件版（约 28.1 MB），双击运行；首次启动会解压，稍慢 |
| `RATGP-v1.0.1-windows-x64-portable.zip` | 目录版（约 50 MB 解压后 / 27.9 MB 压缩），解压后双击 `RATGP\RATGP.exe`；启动更快，受限环境推荐 |

运行环境：Windows 10/11（自带 WebView2 Runtime）。

首次启动：在 `%APPDATA%\RATGP` 建空库，并设置本地锁密码；数据都在该目录，卸载软件不删数据。

> 想先看演示数据：把仓库 `App/data/ratgp.db` 复制到 `%APPDATA%\RATGP\ratgp.db`，或自己上传 `demo/图书馆借阅系统需求_V1.0.docx` 走一遍。

## 验证

- 后端 65 条单元测试全绿；
- 前端 `tsc`、静态构建通过；
- 目录版 exe 实测：启动 → 建项目 → 导出到指定路径成功。

## 已知限制

- 单文件 exe 在禁止写 `%TEMP%` 的受限环境中无法解压，请用目录版；
- 本地锁是单机门禁，不承诺网络级安全；
- AI 功能需要自己的 DeepSeek API Key（BYOK）。
