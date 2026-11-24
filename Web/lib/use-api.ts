"use client";

/**
 * 客户端取数 hook。
 *
 * 静态导出后没有服务端渲染取数，页面全部变成客户端组件：每个页面用 useApi(loader)
 * 拿到 { data, loading, refreshing, error, reload }，自己渲染骨架 / 错误态 / 内容。
 *
 * 刷新靠一个全局事件：写操作（确认、审核、执行、导入、上传、抽取…）成功后调用
 * notifyDataChanged()，所有活着的 useApi 一起重新取数——侧栏数字跟着变，
 * 不再需要 router.refresh()（静态导出下它也刷新不了服务端数据）。
 */
import { useCallback, useEffect, useRef, useState } from "react";

export const DATA_CHANGED_EVENT = "ratgp-data-changed";

/** 广播「数据变了」：所有 useApi 立刻重新取数。 */
export function notifyDataChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(DATA_CHANGED_EVENT));
}

export interface ApiState<T> {
  data: T | null;
  /** 首次加载（还没有任何数据可显示） */
  loading: boolean;
  /** 后台刷新（已有数据，正在取新数据；页面不闪白） */
  refreshing: boolean;
  error: string | null;
  /** 手动重新取数（错误态的「重试」按钮） */
  reload: () => void;
}

/**
 * @param loader 取数函数；内部用 ref 保持最新实现，不会因为函数身份变化重复请求
 * @param deps   额外的重新取数条件（如 projectId、搜索词），变化时重新取数
 */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []): ApiState<T> {
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const hasData = useRef(false);

  useEffect(() => {
    let cancelled = false;
    if (hasData.current) setRefreshing(true);
    else setLoading(true);

    loaderRef.current().then(
      (next) => {
        if (cancelled) return;
        hasData.current = true;
        setData(next);
        setError(null);
        setLoading(false);
        setRefreshing(false);
      },
      (err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "加载失败");
        setLoading(false);
        setRefreshing(false);
      },
    );

    return () => {
      cancelled = true;
    };
    // loader 故意不进依赖：用 ref 取最新实现，避免每次 render 都触发请求
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, ...deps]);

  // 任意写操作广播后重新取数
  useEffect(() => {
    const onChanged = () => setTick((n) => n + 1);
    window.addEventListener(DATA_CHANGED_EVENT, onChanged);
    return () => window.removeEventListener(DATA_CHANGED_EVENT, onChanged);
  }, []);

  const reload = useCallback(() => setTick((n) => n + 1), []);

  return { data, loading, refreshing, error, reload };
}

/**
 * 读地址栏一次性开关（?upload=1 / ?extract=1 这类）。
 * 静态导出下页面在构建时也会预渲染一次，所以只能在 effect 里读 window。
 */
export function useQueryFlag(name: string, value = "1"): boolean {
  const [on, setOn] = useState(false);

  useEffect(() => {
    const sync = () => {
      try {
        setOn(new URLSearchParams(window.location.search).get(name) === value);
      } catch {
        setOn(false);
      }
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [name, value]);

  return on;
}
