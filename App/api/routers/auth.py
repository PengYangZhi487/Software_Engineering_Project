"""本地锁接口：状态 / 首次设置密码 / 登录 / 锁定。

本地单机软件的门禁，取舍见 ``App/services/auth_service.py`` 的模块注释：
token 只存进程内存、只用于这里校验，业务接口不强制拦截。

注意：本 router 需要在 ``App/api/main.py`` 里 ``app.include_router(auth.router)``
才会生效（按团队约定 main.py 由 captain 统一改）。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from App.api.schemas import (
    AuthLoginOut,
    AuthPasswordIn,
    AuthStatusOut,
)
from App.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _status_out() -> AuthStatusOut:
    data = auth_service.status()
    return AuthStatusOut(
        configured=data["configured"],
        locked=data["locked"],
        token_ttl_seconds=data["token_ttl_seconds"],
    )


@router.get("/status", response_model=AuthStatusOut, summary="本地锁状态")
def auth_status() -> AuthStatusOut:
    return _status_out()


@router.post(
    "/setup",
    response_model=AuthStatusOut,
    status_code=status.HTTP_201_CREATED,
    summary="首次设置本地锁密码",
)
def auth_setup(body: AuthPasswordIn) -> AuthStatusOut:
    password = body.password.strip()
    if len(password) < 4:
        raise HTTPException(status_code=422, detail="密码至少 4 位，且不能全是空白")
    if not auth_service.set_password(password):
        raise HTTPException(status_code=409, detail="已经设置过本地锁密码，请直接登录")
    return _status_out()


@router.post("/login", response_model=AuthLoginOut, summary="登录解锁（返回短期 token）")
def auth_login(body: AuthPasswordIn) -> AuthLoginOut:
    token = auth_service.login(body.password)
    if token is None:
        if not auth_service.is_configured():
            raise HTTPException(status_code=409, detail="还没有设置本地锁密码，请先设置")
        raise HTTPException(status_code=401, detail="密码不正确")
    return AuthLoginOut(
        token=token,
        expires_in=auth_service.TOKEN_TTL_SECONDS,
        configured=True,
        locked=False,
    )


@router.post("/lock", response_model=AuthStatusOut, summary="锁定（清空当前登录 token）")
def auth_lock() -> AuthStatusOut:
    auth_service.lock()
    return _status_out()
