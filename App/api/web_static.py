"""把前端静态产物挂到 FastAPI 上，支撑「单进程桌面化」。

设计约束（见 docs/封装说明.md）：

* **不改 main.py**：桌面入口（``desktop.py``）在 ``app`` 创建之后调用
  :func:`mount_web`，纯 API 场景（uvicorn App.api.main:app）完全不受影响。
* **安全跳过**：找不到静态目录时只记一条日志，服务照常以「纯 API」模式运行。
* **深层路由回落**：前端是客户端路由，刷新 ``/requirements`` 这类路径时
  必须回落到 ``index.html``，否则桌面窗口会白屏。

静态目录查找顺序（第一个含 ``index.html`` 的目录生效）：

1. 环境变量 ``RATGP_WEB_DIR``（桌面入口/测试显式指定）
2. PyInstaller 解包目录下的 ``web_dist``（exe 分发）
3. 仓库根目录 ``web_dist``（``tools/build_web.ps1`` 的产物）
4. 仓库根目录 ``Web/out``（``next build`` 静态导出的默认产物）
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.routing import Mount, Route

logger = logging.getLogger("ratgp.api.web_static")

INDEX_NAME = "index.html"

#: 仓库根目录（App/api/web_static.py -> App/api -> App -> 仓库根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _bundle_root() -> Path | None:
    """PyInstaller onefile 模式的解包目录；未打包时为 None。"""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else None


def candidate_dirs(project_root: Path | None = None) -> list[Path]:
    """按优先级返回静态目录候选（可能不存在，调用方负责过滤）。"""
    root = Path(project_root) if project_root else PROJECT_ROOT
    raw: list[Path] = []

    env_dir = os.environ.get("RATGP_WEB_DIR")
    if env_dir:
        raw.append(Path(env_dir).expanduser())

    bundle = _bundle_root()
    if bundle is not None:
        raw.append(bundle / "web_dist")

    raw.append(root / "web_dist")
    raw.append(root / "Web" / "out")

    # 去重（Windows 下大小写不敏感，用 resolve 后的字符串比较）
    seen: set[str] = set()
    dirs: list[Path] = []
    for item in raw:
        try:
            key = str(item.resolve()).lower()
        except OSError:  # pragma: no cover - 路径不可访问时按原样处理
            key = str(item).lower()
        if key in seen:
            continue
        seen.add(key)
        dirs.append(item)
    return dirs


def find_web_dir(project_root: Path | None = None) -> Path | None:
    """返回第一个包含 index.html 的静态目录，找不到返回 None。"""
    for directory in candidate_dirs(project_root):
        if (directory / INDEX_NAME).is_file():
            return directory
    return None


class SPAStaticFiles(StaticFiles):
    """``html=True`` 的 StaticFiles，外加单页应用式回落。

    规则：

    * 未命中且路径没有扩展名（如 ``/requirements``）-> 返回 ``index.html``；
    * 未命中且路径以 ``api/`` 开头 -> 维持 404，保住 API 的 JSON 语义；
    * 未命中但带扩展名（``/missing.js``）-> 维持 404，避免把 HTML 当静态资源。
    """

    def __init__(self, directory: str | Path, **kwargs) -> None:
        kwargs.setdefault("html", True)
        super().__init__(directory=str(directory), **kwargs)

    async def get_response(self, path: str, scope):
        if self._is_api_path(path):
            # 让 FastAPI 的异常处理返回 JSON 404，而不是静态站的 404.html
            raise StarletteHTTPException(status_code=404)

        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or not self._should_fallback(path):
                raise
            return await super().get_response(INDEX_NAME, scope)

        # 静态导出常带 404.html：Starlette 会用它返回 404，而不是抛异常。
        # 对客户端路由来说这仍是「没找到」，要回落到 index.html 交给前端路由。
        if getattr(response, "status_code", 200) == 404 and self._should_fallback(path):
            return await super().get_response(INDEX_NAME, scope)
        return response

    @staticmethod
    def _is_api_path(path: str) -> bool:
        # Windows 上 Starlette 用 os.path.normpath 处理路径，分隔符会变成 "\"
        clean = (path or "").replace("\\", "/").strip("/")
        return clean == "api" or clean.startswith("api/")

    @staticmethod
    def _should_fallback(path: str) -> bool:
        if SPAStaticFiles._is_api_path(path):
            return False
        clean = (path or "").replace("\\", "/").strip("/")
        return not Path(clean).suffix


def _has_mounted_web(app: FastAPI) -> bool:
    return any(isinstance(route, Mount) and route.name == "web" for route in app.router.routes)


def _replace_root_route(app: FastAPI, index_file: Path) -> None:
    """让 ``/`` 返回前端首页，而不是 main.py 里的 API 介绍 JSON。

    main.py 的 ``GET /`` 是纯 API 模式的门面；一旦挂了前端，桌面窗口从 ``/``
    进入必须拿到 index.html。这里替换的是路由对象本身（保留位置），
    不改动 main.py 源码，也不影响其他 API 路由。
    """

    async def index(_request: Request) -> FileResponse:
        return FileResponse(index_file, media_type="text/html; charset=utf-8")

    new_route = Route("/", endpoint=index, methods=["GET"], include_in_schema=False)
    for position, route in enumerate(app.router.routes):
        if (
            isinstance(route, Route)
            and route.path == "/"
            and route.methods
            and "GET" in route.methods
        ):
            app.router.routes[position] = new_route
            return
    app.router.routes.insert(0, new_route)


def mount_web(app: FastAPI, project_root: Path | None = None) -> Path | None:
    """挂载前端静态目录；返回实际使用的目录，跳过时返回 None。

    重复调用是幂等的（已挂载则直接返回目录）。
    """
    web_dir = find_web_dir(project_root)
    if web_dir is None:
        logger.info(
            "未找到 Web 静态产物（RATGP_WEB_DIR / web_dist / Web/out），"
            "跳过静态托管，按纯 API 运行"
        )
        return None

    if _has_mounted_web(app):
        logger.debug("Web 静态目录已挂载，跳过重复挂载：%s", web_dir)
        return web_dir

    index_file = web_dir / INDEX_NAME
    _replace_root_route(app, index_file)
    app.mount(
        "/",
        SPAStaticFiles(directory=web_dir, html=True),
        name="web",
    )
    logger.info("已挂载 Web 静态目录：%s", web_dir)
    return web_dir


__all__ = [
    "INDEX_NAME",
    "PROJECT_ROOT",
    "SPAStaticFiles",
    "candidate_dirs",
    "find_web_dir",
    "mount_web",
]
