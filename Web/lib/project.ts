"use client";

/**
 * 当前项目（多项目支持）。
 *
 * 来源优先级：URL ?project= > localStorage > 1。
 * 切换项目时写 localStorage + 更新地址栏（replaceState，不整页刷新）+ 广播
 * ratgp-project-changed；所有页面的 useApi 依赖 projectId，切换后自动重新取数，
 * 侧栏数字与当前项目名也跟着变。
 *
 * 第一次渲染时还不知道真实项目（静态导出的 HTML 也没有），所以 ready=false，
 * 页面据此显示骨架，避免先用 1 号项目的数据闪一下再切换。
 */
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "ratgp-project-id";
export const PROJECT_CHANGED_EVENT = "ratgp-project-changed";

function parseId(value: string | null): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : null;
}

export function readProjectId(): number {
  if (typeof window === "undefined") return 1;
  try {
    const fromUrl = parseId(new URLSearchParams(window.location.search).get("project"));
    if (fromUrl) return fromUrl;
    const stored = parseId(localStorage.getItem(STORAGE_KEY));
    if (stored) return stored;
  } catch {
    /* 隐私模式 / 访问被拒时退回默认项目 */
  }
  return 1;
}

/** 切换当前项目：记忆 + 地址栏 + 广播事件。 */
export function setCurrentProjectId(projectId: number): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, String(projectId));
  } catch {
    /* 忽略存储失败 */
  }
  try {
    const url = new URL(window.location.href);
    url.searchParams.set("project", String(projectId));
    window.history.replaceState(null, "", url.toString());
  } catch {
    /* 地址栏不可写时只靠 localStorage */
  }
  window.dispatchEvent(new Event(PROJECT_CHANGED_EVENT));
}

export interface CurrentProject {
  projectId: number;
  /** 已经从地址栏 / localStorage 读到真实项目 id（首帧为 false） */
  ready: boolean;
  setProjectId: (projectId: number) => void;
}

export function useCurrentProject(): CurrentProject {
  const [state, setState] = useState<{ id: number; ready: boolean }>({ id: 1, ready: false });

  useEffect(() => {
    const sync = () => setState({ id: readProjectId(), ready: true });
    sync();
    window.addEventListener(PROJECT_CHANGED_EVENT, sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener(PROJECT_CHANGED_EVENT, sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  const setProjectId = useCallback((projectId: number) => {
    setCurrentProjectId(projectId);
    setState({ id: projectId, ready: true });
  }, []);

  return { projectId: state.id, ready: state.ready, setProjectId };
}
