"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "./icon";
import { ThemeMenu } from "./theme-menu";
import { titleOf } from "@/lib/nav";

export function Topbar() {
  const pathname = usePathname();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");

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
    router.push(value ? `/requirements?q=${encodeURIComponent(value)}` : "/requirements");
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
          placeholder="搜索需求编号、标题…"
          aria-label="搜索需求"
          autoComplete="off"
        />
        <span className="kbd">/</span>
      </form>

      <div className="tb-div" />
      <ThemeMenu />
      <div className="avatar">管</div>
    </header>
  );
}
