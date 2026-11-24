# RATGP v1.0.0 发布说明

## 这是什么

RATGP 是一个**需求与测试用例管理台**：把需求文档变成结构化、可确认、可追溯的需求，
按确认结果生成测试用例，并把「需求 ↔ 用例 ↔ 变更 ↔ 执行」串成可复算的闭环。

AI（大模型）只负责加速录入和生成候选；确认、审核、执行、交付都由人完成。

## 主要功能

- **需求**：文档解析（docx/txt，含表格）、AI 抽取候选、人工确认/驳回、批量操作、手动新建/编辑
- **质量**：模糊词、数值冲突、缺验收条件扫描；按内容指纹保存裁决
- **用例**：按已确认需求生成正常/异常/边界候选；审核/驳回/批量审核
- **执行记录**：用例的真实执行结果、实际结果、comments、执行人、签名、环境
- **追踪**：需求 × 用例矩阵、覆盖率（已审核用例口径，SQL 可复算）
- **变更**：两版文档段落级比对、受影响需求/用例、改版提醒
- **报告**：Excel（概览 / 需求清单 / 测试用例执行表 / 覆盖矩阵）与 CSV
- **导入导出**：需求/用例清单 xlsx、Word 需求表、粘贴大模型 JSON；导出→Excel 改→导入闭环
- **多项目**：项目选择器、新建/重命名/删除
- **本地锁**：首次设置密码，解锁后使用（单机门禁）
- **桌面版**：FastAPI + pywebview 单进程窗口，数据在 `%APPDATA%\RATGP`

## 下载与运行

两个资产任选其一：

| 资产 | 用法 |
|---|---|
| `RATGP.exe`（单文件，约 28 MB） | 双击运行；首次启动稍慢（解压）。若提示 `PYI: Failed to create parent directory structure`，改用目录版 |
| `RATGP-v1.0.0-windows-x64-portable.zip`（目录版，约 50 MB） | 解压后双击 `RATGP\RATGP.exe`；启动更快，不依赖临时目录解压 |

运行环境：Windows 10/11 + WebView2 Runtime（系统一般自带）。

首次启动会：

1. 在 `%APPDATA%\RATGP` 创建数据目录和空数据库；
2. 引导设置本地锁密码（可跳过？——不会跳过，必须设置）；
3. 进入总览页。

**想把演示数据带进去**：把仓库里的 `App/data/ratgp.db` 复制到 `%APPDATA%\RATGP\ratgp.db`。

**API Key**：抽取/生成用例需要 DeepSeek Key（BYOK）。桌面版右上角「钥匙」按钮填入，
只存在当前标签页的 sessionStorage，不落盘；或启动前设环境变量 `DEEPSEEK_API_KEY`。

## 从源码运行

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r App\requirements.txt
cd Web; npm install; cd ..
.\tools\demo.ps1          # 起后端 + 前端 + 打开浏览器
```

详细步骤见仓库根目录 `README.md`。

## 验证

- 后端 60 条单元测试（`python -m unittest discover -s App\api\tests`）
- 前端 `tsc --noEmit`、静态构建通过
- 桌面版 headless 冒烟：`/api/health`、首页、深层路由、API 404 均通过

## 已知限制

- 本地锁是**单机门禁**，防的是别人随手打开改数据；数据库就在本机，不承诺网络级安全；
- 单文件 exe 在禁止写 `%TEMP%` 的受限环境中无法解压，请用目录版；
- 未内置 API Key，首次使用需要自己的 DeepSeek Key；
- 语义级冲突检测、多人协作/账号体系尚未实现（规划中）。
