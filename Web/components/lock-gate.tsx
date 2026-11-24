"use client";

/**
 * 本地锁前端：未解锁时挡住工作台（不渲染侧栏/页面，也就不发业务请求）。
 *
 * 三种界面：
 * - 首次使用（configured=false）：设置密码向导（至少 4 位，输两遍）
 * - 已配置且锁定 / 本会话没有 token：登录框
 * - 读取锁状态失败：提示 + 重试（不提供「跳过」，避免绕过门禁）
 *
 * 口径：这是本地单机软件的门禁，用来防止别人随手打开改数据；数据库文件就在
 * 这台电脑上，业务接口不做全局拦截，不承诺网络级安全。
 */
import { useEffect, useState, type ReactNode } from "react";
import { ApiError, lockApp, loginLock, setupLockPassword } from "@/lib/api";
import { clearLockToken, getLockToken, notifyLockChanged, setLockToken, useLockState } from "@/lib/auth";
import { Icon } from "./icon";

function Brand() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 9,
          background: "var(--accent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "none",
        }}
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
          <path d="M4 7h16M4 12h11M4 17h14" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: 14.5, fontWeight: 650, letterSpacing: "-.01em" }}>RATGP</div>
        <div style={{ fontSize: 11, color: "var(--text-3)" }}>需求工程工作台 · 本地锁</div>
      </div>
    </div>
  );
}

function Frame({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        background: "var(--bg)",
      }}
    >
      <div style={{ width: "min(430px, 100%)" }}>
        <Brand />
        {children}
        <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-3)", lineHeight: 1.7, textAlign: "center" }}>
          本地锁只防止别人随手打开软件改数据；数据库就在这台电脑上，不提供网络级安全。
        </div>
      </div>
    </div>
  );
}

export function LockBooting() {
  return (
    <Frame>
      <div className="card">
        <div className="empty" style={{ padding: "38px 20px" }}>
          <div className="ic loading-pulse">
            <Icon name="shield" size={20} />
          </div>
          <h3>正在检查本地锁…</h3>
          <p>读取后端锁状态。</p>
        </div>
      </div>
    </Frame>
  );
}

export function LockError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Frame>
      <div className="card">
        <div className="empty" style={{ padding: "34px 20px" }}>
          <div className="ic">
            <Icon name="alert" size={20} />
          </div>
          <h3>读不到本地锁状态</h3>
          <p>{message}</p>
          <code className="codeblock">
            .\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000
          </code>
          <div className="row">
            <button className="btn primary" type="button" onClick={onRetry}>
              重试
            </button>
          </div>
        </div>
      </div>
    </Frame>
  );
}

export function LockScreen({
  mode,
  onUnlocked,
}: {
  mode: "setup" | "login";
  onUnlocked: () => void;
}) {
  const [current, setCurrent] = useState<"setup" | "login">(mode);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setCurrent(mode);
    setError(null);
  }, [mode]);

  async function submit() {
    setError(null);
    setNotice(null);
    const value = password.trim();
    if (value.length < 4) {
      setError("密码至少 4 位");
      return;
    }

    setBusy(true);
    try {
      if (current === "setup") {
        if (value !== confirm.trim()) {
          setError("两次输入的密码不一致");
          return;
        }
        await setupLockPassword(value);
        setNotice("密码已设置。请用刚才的密码登录一次解锁。");
        setCurrent("login");
        setPassword("");
        setConfirm("");
        return;
      }

      const result = await loginLock(value);
      setLockToken(result.token);
      notifyLockChanged();
      onUnlocked();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("密码不正确");
      } else if (err instanceof ApiError && err.status === 409 && current === "login") {
        setError("还没有设置本地锁密码，请先设置");
        setCurrent("setup");
      } else if (err instanceof ApiError && err.status === 409) {
        setError("已经设置过密码，请直接登录");
        setCurrent("login");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("密码不符合要求（至少 4 位，且不能全是空白）");
      } else {
        setError(err instanceof Error ? err.message : "操作失败");
      }
    } finally {
      setBusy(false);
    }
  }

  const isSetup = current === "setup";

  return (
    <Frame>
      <div className="card">
        <div className="card-h">
          <Icon name={isSetup ? "key" : "shield"} size={15} />
          <span className="t">{isSetup ? "第一次使用：设置本地锁密码" : "已锁定"}</span>
          <span className="m">{isSetup ? "至少 4 位" : "输入密码解锁"}</span>
        </div>
        <div className="card-b" style={{ display: "flex", flexDirection: "column", gap: 11 }}>
          {isSetup ? (
            <p style={{ margin: 0, fontSize: 12, lineHeight: 1.8, color: "var(--text-2)" }}>
              给这台电脑上的 RATGP 设一个本地锁密码（至少 4 位）。设置后需要登录一次才能进入；
              以后每次打开软件或点「锁定」后都要输入。
            </p>
          ) : (
            <p style={{ margin: 0, fontSize: 12, lineHeight: 1.8, color: "var(--text-2)" }}>
              输入本地锁密码解锁工作台。刷新页面保持解锁，关闭窗口后需要重新登录。
            </p>
          )}

          <label className="field">
            <span>{isSetup ? "设置密码" : "密码"}</span>
            <input
              type="password"
              value={password}
              autoFocus
              autoComplete={isSetup ? "new-password" : "current-password"}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void submit();
              }}
              placeholder={isSetup ? "至少 4 位" : "输入密码"}
            />
          </label>

          {isSetup ? (
            <label className="field">
              <span>再输一次</span>
              <input
                type="password"
                value={confirm}
                autoComplete="new-password"
                onChange={(e) => setConfirm(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void submit();
                }}
                placeholder="确认密码"
              />
            </label>
          ) : null}

          {notice ? <div className="extract-status ok">{notice}</div> : null}
          {error ? (
            <div className="upload-err" style={{ padding: 0 }}>
              {error}
            </div>
          ) : null}

          <button className="btn primary" type="button" onClick={submit} disabled={busy}>
            {busy ? "处理中…" : isSetup ? "设置密码" : "解锁"}
          </button>

          {!isSetup ? (
            <div style={{ fontSize: 11, color: "var(--text-3)", lineHeight: 1.7 }}>
              忘记密码：本地锁没有找回入口，需要清空数据目录里的本地锁记录后重新设置
              （见 README「本地锁」一节）。
            </div>
          ) : null}
        </div>
      </div>
    </Frame>
  );
}

/** 顶层门禁：未解锁时只渲染锁屏，工作台（侧栏 + 页面）不挂载、不发业务请求。 */
export function LockGate({ children }: { children: ReactNode }) {
  const lock = useLockState();

  if (!lock.ready) return <LockBooting />;
  if (lock.error) return <LockError message={lock.error} onRetry={lock.refresh} />;
  if (lock.needsSetup) return <LockScreen mode="setup" onUnlocked={lock.refresh} />;
  if (lock.needsLogin) return <LockScreen mode="login" onUnlocked={lock.refresh} />;
  return <>{children}</>;
}

/** 顶栏「锁定」：先让后端清 token，再清本地 token 并广播，LockGate 会回到锁屏。 */
export async function lockNow(): Promise<void> {
  try {
    await lockApp();
  } catch {
    /* 后端不可用时仍然清本地 token，回到锁屏 */
  }
  clearLockToken();
  notifyLockChanged();
}

/** 判断当前是否已经解锁（给需要主动校验的组件用）。 */
export function hasLockToken(): boolean {
  return Boolean(getLockToken());
}
