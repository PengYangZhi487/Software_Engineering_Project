"use client";

import { useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "./icon";

const THEMES: { id: string; name: string; icon: IconName; swatch: string }[] = [
  { id: "light", name: "浅色", icon: "sun", swatch: "sw light" },
  { id: "glass", name: "玻璃淡紫", icon: "drop", swatch: "sw glass" },
  { id: "dark", name: "深色", icon: "moon", swatch: "sw dark" },
];

export function ThemeMenu() {
  const [theme, setTheme] = useState("light");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // 浏览器端读取已保存主题（首屏由 layout 的内联脚本先打上，避免闪烁）
  useEffect(() => {
    const t = document.documentElement.dataset.theme;
    setTheme(t === "glass" || t === "dark" ? t : "light");
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function apply(id: string) {
    setTheme(id);
    document.documentElement.dataset.theme = id;
    try {
      localStorage.setItem("ratgp-theme", id);
    } catch {
      /* 隐私模式下忽略 */
    }
    setOpen(false);
  }

  const current = THEMES.find((t) => t.id === theme) ?? THEMES[0];

  return (
    <div className={`tmenu${open ? " on" : ""}`} ref={wrapRef}>
      <button
        type="button"
        className="btn icon ghost"
        title={`主题：${current.name}`}
        aria-label="切换主题"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name={current.icon} size={15} />
      </button>

      <div className="tpop">
        <div className="tpop-h">主题</div>
        {THEMES.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`titem${t.id === theme ? " on" : ""}`}
            onClick={() => apply(t.id)}
          >
            <span className={t.swatch} />
            {t.name}
          </button>
        ))}
      </div>
    </div>
  );
}
