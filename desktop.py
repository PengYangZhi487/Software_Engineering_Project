#!/usr/bin/env python
"""RATGP 桌面入口：单进程（FastAPI/uvicorn 后台线程）+ pywebview 原生窗口。

为什么是单进程：

* 后端（FastAPI）跑在 127.0.0.1 的随机端口上，前端静态产物由同一个进程托管，
  不需要额外起 Node、不需要用户手动开浏览器；
* 数据库、上传文件、日志、备份全部收进用户数据目录，安装/卸载都不碰程序目录。

用法::

    python desktop.py                 # 打开桌面窗口（默认）
    python desktop.py --no-window     # 只起本地服务，不开窗口（排查/CI 用）
    python desktop.py --port 8123     # 固定端口（默认自动挑空闲端口）
    python desktop.py --data-dir D:\\RATGP-data   # 临时换数据目录
    python desktop.py --debug         # 打开 webview 调试工具 + DEBUG 日志

数据目录（首次运行自动创建）::

    Windows: %APPDATA%\\RATGP
    macOS:   ~/Library/Application Support/RATGP
    Linux:   $XDG_DATA_HOME/RATGP 或 ~/.local/share/RATGP

可用环境变量覆盖：

* ``RATGP_DATA_DIR`` 数据目录
* ``RATGP_DB``       数据库文件（默认 <数据目录>/ratgp.db）
* ``RATGP_WEB_DIR``  前端静态目录（默认自动查找 web_dist / Web/out）

注意：``App/api/config.py`` 与 ``App/dao/db.py`` 在 **导入时** 读取上述环境变量，
所以本模块必须先准备好环境变量，再 ``import App.api.main``（见 :func:`main`）。
"""
from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_NAME = "RATGP"
WINDOW_TITLE = "RATGP 需求解析与测试用例辅助生成平台"
HEALTH_PATH = "/api/health"
PROJECT_ROOT = Path(__file__).resolve().parent

LOGGER_NAME = "ratgp.desktop"
LOG = logging.getLogger(LOGGER_NAME)

DATA_DIR_README = """RATGP 数据目录
================

这个目录由 RATGP 桌面版自动创建，删除它等于清空本机数据。

  ratgp.db     SQLite 数据库（项目、文档、需求、用例、执行记录）
  uploads/     上传的 Word/TXT 原文件
  backups/     tools/backup.ps1 生成的数据库备份
  logs/        运行日志（排查问题用）

迁移/换机：把整个目录复制到新机器的 %APPDATA%\\RATGP 即可。
备份：关闭 RATGP 后复制 ratgp.db，或运行 tools/backup.ps1。
"""


# --------------------------------------------------------------------------- #
# 数据目录与环境变量
# --------------------------------------------------------------------------- #
def default_data_dir() -> Path:
    """按平台返回默认数据目录（不创建）。"""
    override = os.environ.get("RATGP_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / APP_NAME


def prepare_environment(data_dir: Path) -> Path:
    """创建数据目录并注入环境变量，返回数据库路径。

    必须在 ``import App.api.main`` 之前调用。
    """
    data_dir = data_dir.expanduser().resolve()
    uploads = Path(os.environ.get("RATGP_UPLOAD_DIR") or data_dir / "uploads").expanduser()
    db_path = Path(os.environ.get("RATGP_DB") or data_dir / "ratgp.db").expanduser().resolve()

    for directory in (data_dir, data_dir / "logs", data_dir / "backups", uploads, db_path.parent):
        directory.mkdir(parents=True, exist_ok=True)

    # 统一注入：config.py / db.py 都在导入时读取这些变量
    os.environ["RATGP_DATA_DIR"] = str(data_dir)
    os.environ["RATGP_UPLOAD_DIR"] = str(uploads)
    os.environ["RATGP_DB"] = str(db_path)

    # 首次运行时放一份说明，用户打开 %APPDATA%\RATGP 就知道每个文件干什么
    marker = data_dir / "README.txt"
    if not marker.exists():
        try:
            marker.write_text(DATA_DIR_README, encoding="utf-8")
        except OSError:  # 只读介质等场景不阻塞启动
            pass
    return db_path


# --------------------------------------------------------------------------- #
# 日志
# --------------------------------------------------------------------------- #
def _setup_logging(data_dir: Path, verbose: bool = False) -> None:
    """控制台 + 数据目录日志文件双写；文件写入失败不影响启动。"""
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        log_dir = data_dir.expanduser() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "desktop.log", encoding="utf-8"))
    except OSError as exc:  # pragma: no cover - 权限异常时降级
        print(f"[warn] 无法写日志文件，仅输出到控制台：{exc}", file=sys.stderr)

    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=handlers, force=True)

    # uvicorn 用标准 logging，不额外配置（log_config=None），跟着 root 走
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "ratgp.api", "ratgp.api.web_static"):
        logging.getLogger(name).setLevel(level)


# --------------------------------------------------------------------------- #
# 端口 / HTTP 服务
# --------------------------------------------------------------------------- #
def pick_port(preferred: int | None = None) -> int:
    """固定端口原样返回；否则向系统要一个空闲端口。"""
    if preferred is not None:
        if not 1 <= preferred <= 65535:
            raise ValueError(f"端口不合法：{preferred}")
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ApiServer:
    """在后台线程里跑 uvicorn；窗口关闭时用 :meth:`stop` 优雅退出。"""

    def __init__(self, app, host: str, port: int, log_level: str = "info") -> None:
        import uvicorn

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level=log_level,
            log_config=None,  # 复用 desktop.py 的 handler（含日志文件）
            access_log=False,
            lifespan="on",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, name="ratgp-uvicorn", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._server.should_exit = True
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():  # pragma: no cover - 极端情况
                LOG.warning("uvicorn 线程未在 %.0fs 内退出，随进程结束", timeout)


def wait_for_server(base_url: str, timeout: float = 30.0, interval: float = 0.2) -> bool:
    """轮询 /api/health，直到后端可用或超时。"""
    deadline = time.monotonic() + timeout
    health_url = f"{base_url}{HEALTH_PATH}"
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                if 200 <= response.status < 300:
                    return True
                last_error = f"HTTP {response.status}"
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last_error = str(exc)
        time.sleep(interval)
    LOG.warning("健康检查未通过（%s）：%s", health_url, last_error or "超时")
    return False


# --------------------------------------------------------------------------- #
# 窗口
# --------------------------------------------------------------------------- #
def _load_webview():
    """导入 pywebview；未安装时给出可执行的修复提示。"""
    try:
        import webview  # noqa: F401  延迟导入：--no-window 模式不需要
    except ImportError:
        LOG.error(
            "未安装 pywebview，无法打开桌面窗口。请先安装：\n"
            "    python -m pip install pywebview\n"
            "或先用无窗口模式排查后端：python desktop.py --no-window"
        )
        return None
    return webview


def _run_window(webview, url: str, debug: bool = False) -> None:
    """打开原生窗口；阻塞到窗口关闭。"""
    # pywebview 默认 ALLOW_DOWNLOADS=False：<a download> 会被直接 Cancel，
    # 表现为「点导出没反应」。打开开关后 WebView2 会弹另存为对话框。
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
    except Exception:  # 旧版 pywebview 没有 settings 字典
        LOG.warning("当前 pywebview 不支持 ALLOW_DOWNLOADS，导出可能无法保存")

    window = webview.create_window(
        WINDOW_TITLE,
        url,
        width=1440,
        height=900,
        min_size=(1024, 700),
    )
    LOG.info("正在打开桌面窗口：%s", url)
    webview.start(debug=debug)
    LOG.info("窗口已关闭：%s", getattr(window, "title", url))


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RATGP 桌面客户端（单进程：FastAPI + pywebview）"
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="只启动本地 HTTP 服务，不开窗口（调试 / CI / 冒烟测试）",
    )
    parser.add_argument(
        "--port", type=int, default=None, help="固定端口（默认自动挑空闲端口）"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="监听地址（默认只对本机开放，桌面场景不要改成 0.0.0.0）",
    )
    parser.add_argument(
        "--data-dir", default=None, help="数据目录（等价于设置 RATGP_DATA_DIR）"
    )
    parser.add_argument(
        "--db", default=None, help="数据库文件（等价于设置 RATGP_DB）"
    )
    parser.add_argument(
        "--debug", action="store_true", help="打开 webview 调试工具并输出 DEBUG 日志"
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=30.0,
        help="等待后端就绪的秒数（默认 30）",
    )
    parser.add_argument(
        "--exit-after",
        type=float,
        default=0.0,
        help="（调试，仅 --no-window）服务就绪后运行 N 秒自动退出；0 表示一直运行",
    )
    return parser


def _wait_seconds(seconds: float) -> None:
    """等待指定秒数；Ctrl+C 时干净退出。"""
    stopped = threading.Event()
    try:
        stopped.wait(seconds if seconds > 0 else None)
    except KeyboardInterrupt:
        LOG.info("收到 Ctrl+C，正在退出")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 命令行优先于环境变量；两者都要在 import App 之前生效
    if args.data_dir:
        os.environ["RATGP_DATA_DIR"] = args.data_dir
    if args.db:
        os.environ["RATGP_DB"] = args.db

    data_dir = Path(args.data_dir) if args.data_dir else default_data_dir()
    _setup_logging(data_dir, verbose=args.debug)
    LOG.info("RATGP 桌面版启动（Python %s）", sys.version.split()[0])

    try:
        db_path = prepare_environment(data_dir)
    except OSError as exc:
        LOG.error("初始化数据目录失败：%s", exc)
        return 2

    LOG.info("数据目录：%s", data_dir)
    LOG.info("数据库：%s", db_path)

    # 延迟导入：环境变量就位后 App 层才会读到正确路径
    from App.api.main import app  # noqa: PLC0415
    from App.api.web_static import candidate_dirs, find_web_dir, mount_web  # noqa: PLC0415

    if find_web_dir(PROJECT_ROOT) is None:
        LOG.warning(
            "未找到前端静态产物，窗口将只显示 API 门面。先运行 tools/build_web.ps1，"
            "候选目录：%s",
            " | ".join(str(item) for item in candidate_dirs(PROJECT_ROOT)),
        )
    mount_web(app, PROJECT_ROOT)

    try:
        port = pick_port(args.port)
    except ValueError as exc:
        LOG.error("%s", exc)
        return 2
    base_url = f"http://{args.host}:{port}"

    server = ApiServer(app, args.host, port, log_level="debug" if args.debug else "info")
    try:
        server.start()
        if not wait_for_server(base_url, timeout=args.health_timeout):
            LOG.error("后端在 %.0fs 内未就绪：%s%s", args.health_timeout, base_url, HEALTH_PATH)
            return 3
        LOG.info("后端已就绪：%s", base_url)

        if args.no_window:
            LOG.info("无窗口模式运行中（Ctrl+C 退出）")
            _wait_seconds(args.exit_after)
            return 0

        webview = _load_webview()
        if webview is None:
            return 4
        _run_window(webview, base_url, debug=args.debug)
        return 0
    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
