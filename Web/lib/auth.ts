"use client";

/**
 * 本地锁的前端状态。
 *
 * 解锁凭据（后端发的短期 token）只放 sessionStorage：刷新还在、关标签页失效；
 * 不用 localStorage，避免下次开机还自动解锁。
 *
 * 判定规则（与后端 auth_service 的语义对齐）：
 * - configured=false          → 首次设置密码向导
 * - configured=true 且 locked  → 登录框（token 已失效）
 * - configured=true 且未锁、但本会话没有 token → 也要求登录（关标签页后 token 没了，
 *   后端可能仍是未锁状态，所以前端自己把关）
 * - configured=true 且未锁、且有 token → 放行
 *
 * 注意这是「防止别人随手打开软件改数据」的轻量门禁：业务接口不做全局拦截，
 * 数据库文件就在本机磁盘上，不能承诺网络级安全。
 */
import { useCallback, useEffect, useState } from "react";
import { getAuthStatus, type AuthStatus } from "./api";

const TOKEN_KEY = "ratgp-lock-token";
export const LOCK_CHANGED_EVENT = "ratgp-lock-changed";

export function getLockToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setLockToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* 隐私模式忽略 */
  }
}

export function clearLockToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

/** 广播锁状态变化（锁定、解锁、设置密码后），LockGate 会重新读 /api/auth/status。 */
export function notifyLockChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(LOCK_CHANGED_EVENT));
}

export interface LockState {
  ready: boolean;
  status: AuthStatus | null;
  error: string | null;
  needsSetup: boolean;
  needsLogin: boolean;
  refresh: () => void;
}

export function useLockState(): LockState {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    getAuthStatus().then(
      (next) => {
        if (cancelled) return;
        setStatus(next);
        setError(null);
        setHasToken(Boolean(getLockToken()));
        setReady(true);
      },
      (err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "无法读取本地锁状态");
        setReady(true);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [tick]);

  useEffect(() => {
    const onChanged = () => setTick((n) => n + 1);
    window.addEventListener(LOCK_CHANGED_EVENT, onChanged);
    return () => window.removeEventListener(LOCK_CHANGED_EVENT, onChanged);
  }, []);

  const refresh = useCallback(() => setTick((n) => n + 1), []);

  const configured = status?.configured ?? false;
  const locked = status?.locked ?? false;

  return {
    ready,
    status,
    error,
    needsSetup: ready && !error && status !== null && !configured,
    needsLogin: ready && !error && status !== null && configured && (locked || !hasToken),
    refresh,
  };
}
