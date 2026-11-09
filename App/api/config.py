"""API 层配置。全部支持环境变量覆盖，方便本地联调与测试。"""
from __future__ import annotations

import os
from pathlib import Path

# App/ 目录（本文件的上一级）
APP_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("RATGP_DATA_DIR") or (APP_DIR / "data"))
UPLOAD_DIR = Path(os.environ.get("RATGP_UPLOAD_DIR") or (DATA_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = int(os.environ.get("RATGP_MAX_UPLOAD_MB", "10")) * 1024 * 1024

ALLOWED_EXTS = {".docx", ".txt"}

_default_origins = ",".join(
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ]
)
CORS_ORIGINS = [o.strip() for o in os.environ.get("RATGP_CORS", _default_origins).split(",") if o.strip()]
