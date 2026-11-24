"""本地锁：单机桌面软件用的进程内轻量门禁。

设计取舍（本地单机，不追求网络级安全）：

- 密码存 ``User`` 表的保留账号 ``__local_lock__`` 上，格式
  ``pbkdf2_sha256$迭代次数$盐$摘要``，不存明文；``init_db`` 建的 admin
  默认账号（sha256("123456")）不复用、不覆盖。
- 登录成功发一个短期 token，只存在进程内存（``dict``），重启即失效；
  进程刚起来时视为「已配置则锁定」。
- **业务接口不做全局拦截**：token 只由 ``/api/auth/*`` 校验，业务 API
  仍可被本机直接调用。理由很实在——数据库文件就在用户磁盘上，能读文件的人
  绕得过任何进程内鉴权；这里的目标是「防止别人随手打开软件改数据」，
  不是网络安全的认证授权。真要更强，需要数据库文件加密或多用户服务端架构。
- 「锁定」= 清空内存 token + 置 locked；``/api/auth/status`` 返回
  ``configured``（是否设置过密码）与 ``locked``（当前是否要输入密码）。

本模块只做状态与校验，不抛 HTTP 异常；协议层转换在 ``routers/auth.py``。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

from App.dao.db import get_connection

LOCK_USERNAME = "__local_lock__"
HASH_ALGO = "pbkdf2_sha256"
ITERATIONS = 100_000
TOKEN_TTL_SECONDS = 8 * 3600

_lock = threading.Lock()
_tokens: dict[str, float] = {}  # token -> 过期时间戳（epoch 秒），进程内存保存
_locked = True  # 进程内状态：已配置密码时，启动后默认锁定


def _stored_hash() -> str | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT password_hash FROM User WHERE username = ?", (LOCK_USERNAME,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    stored = row["password_hash"] or ""
    return stored if stored.startswith(f"{HASH_ALGO}$") else None


def is_configured() -> bool:
    """是否已经设置过本地锁密码。"""
    return _stored_hash() is not None


def is_locked() -> bool:
    """当前是否需要输入密码（没设置密码时不算锁定）。"""
    return is_configured() and _locked


def status() -> dict:
    configured = is_configured()
    return {
        "configured": configured,
        "locked": configured and _locked,
        "token_ttl_seconds": TOKEN_TTL_SECONDS,
    }


def _make_hash(password: str, *, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{HASH_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def _verify_hash(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        if algo != HASH_ALGO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def set_password(password: str) -> bool:
    """首次设置密码；已经设置过返回 False（协议层转 409）。

    设置完成后回到「锁定」状态，需要再登录一次才解锁。
    """
    global _locked
    if not password:
        return False
    with _lock:
        if is_configured():
            return False
        stored = _make_hash(password)
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO User (username, password_hash, display_name, role)
                VALUES (?, ?, ?, 'local')
                ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash
                """,
                (LOCK_USERNAME, stored, "本地锁"),
            )
            conn.commit()
        finally:
            conn.close()
        _locked = True
        _tokens.clear()
        return True


def check_password(password: str) -> bool:
    stored = _stored_hash()
    if not stored or not password:
        return False
    return _verify_hash(password, stored)


def login(password: str) -> str | None:
    """校验密码，成功则发一个进程内 token 并解锁；失败返回 None。"""
    global _locked
    with _lock:
        if not check_password(password):
            return None
        token = secrets.token_urlsafe(32)
        _tokens[token] = time.time() + TOKEN_TTL_SECONDS
        _locked = False
        return token


def lock() -> None:
    """锁定：清空所有内存 token，之后需要重新登录。"""
    global _locked
    with _lock:
        _locked = True
        _tokens.clear()


def validate_token(token: str | None) -> bool:
    """校验 token 是否有效（未锁定、未过期）。供未来可选鉴权依赖使用。"""
    if not token:
        return False
    with _lock:
        if is_locked():
            return False
        expires_at = _tokens.get(token)
        if expires_at is None:
            return False
        if expires_at <= time.time():
            _tokens.pop(token, None)
            return False
        return True
