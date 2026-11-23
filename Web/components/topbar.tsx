"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "./icon";
import { ThemeMenu } from "./theme-menu";
import { ApiKeyDialog } from "./api-key-dialog";
import { getApiKey } from "@/lib/api";
import { titleOf } from "@/lib/nav";

export function Topbar() {
  const pathname = usePathname();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [keyOpen, setKeyOpen] = useState(false);
  const [hasKey, setHasKey] = useState(false);

  // key 状态：顶栏小圆点 + 任意页面都能通过事件唤起设置弹窗
  useEffect(() => {
    const sync = () => setHasKey(Boolean(getApiKey()));
    const openDialog = () => setKeyOpen(true);
    sync();
    window.addEventListener("ratgp-key-changed", sync);
    window.addEventListener("ratgp-open-key-dialog", openDialog);
    return () => {
      window.removeEventListener("ratgp-key-changed", sync);
      window.removeEventListener("ratgp-open-key-dialog", openDialog);
    };
  }, []);

  // 快捷键 / 聚焦搜索
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = inputRef.current;
      if (!el) return;
      if (e.key === "/" && document.activeElement !== el) {
        e.preventDefault();
        el.focus();
        el.select();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // 地址栏里的 ?q= 同步回搜索框（刷新/分享链接后不回空）
  useEffect(() => {
    const qs = new URLSearchParams(window.location.search).get("q");
    setQ(qs ?? "");
  }, [pathname]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const value = q.trim();
    router.push(value ? `/search?q=${encodeURIComponent(value)}` : "/search");
  }

  return (
    <header className="topbar">
      <div className="crumb">
        校园选课系统 <span className="sep">/</span> <b>{titleOf(pathname)}</b>
      </div>

      <form className="searchbox" role="search" onSubmit={submit}>
        <Icon name="search" size={14} />
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜索需求 / 用例 / 问题…"
          aria-label="搜索需求"
          autoComplete="off"
        />
        <span className="kbd">/</span>
      </form>

      <div className="tb-div" />
      <button
        type="button"
        className="btn icon ghost keybtn"
        title={hasKey ? "API Key 已配置，点击修改" : "未配置 API Key，点击设置"}
        aria-label="设置 API Key"
        onClick={() => setKeyOpen(true)}
      >
        <Icon name="key" size={15} />
        {hasKey ? null : <span className="keydot" />}
      </button>
      <ThemeMenu />
      <div className="avatar">管</div>

      <ApiKeyDialog open={keyOpen} onClose={() => setKeyOpen(false)} />
    </header>
  );
}
