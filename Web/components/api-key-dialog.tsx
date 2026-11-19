"use client";

import { useEffect, useState } from "react";
import { clearApiKey, getApiKey, setApiKey } from "@/lib/api";
import { Icon } from "./icon";

/**
 * DeepSeek API Key 设置弹窗（BYOK）。
 *
 * key 只写进 sessionStorage：刷新还在、关掉标签页失效，不进数据库、不进日志。
 * 保存/清除后 dispatch "ratgp-key-changed"，顶栏的小圆点据此更新。
 */
export function ApiKeyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [value, setValue] = useState("");
  const [reveal, setReveal] = useState(false);
  const [saved, setSaved] = useState(false);
  const [hasKey, setHasKey] = useState(false);

  useEffect(() => {
    if (!open) return;
    const existing = getApiKey() ?? "";
    setValue(existing);
    setHasKey(Boolean(existing));
    setSaved(false);
    setReveal(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  function save() {
    const key = value.trim();
    if (key) setApiKey(key);
    else clearApiKey();
    setHasKey(Boolean(key));
    setSaved(true);
  }

  function remove() {
    clearApiKey();
    setValue("");
    setHasKey(false);
    setSaved(false);
  }

  return (
    <>
      <div className="scrim on" onClick={onClose} />
      <div className="keydlg" role="dialog" aria-modal="true" aria-label="设置 DeepSeek API Key">
        <div className="keydlg-h">
          <Icon name="key" size={15} />
          <span className="t">设置 DeepSeek API Key</span>
          <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
            <Icon name="x" size={15} />
          </button>
        </div>

        <div className="keydlg-b">
          <p>
            平台用你自己的 key 调用大模型，费用记在你的账号上。key 只保存在当前标签页的
            sessionStorage 里：刷新还在，关掉标签页即失效；不写数据库、不进日志、不进代码。
          </p>

          <div className="keyrow">
            <input
              type={reveal ? "text" : "password"}
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                setSaved(false);
              }}
              placeholder="sk-..."
              autoComplete="off"
              spellCheck={false}
              aria-label="DeepSeek API Key"
            />
            <button className="btn ghost" type="button" onClick={() => setReveal((v) => !v)}>
              {reveal ? "隐藏" : "显示"}
            </button>
          </div>

          <p className="keydlg-note">
            还没有 key？去{" "}
            <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer">
              platform.deepseek.com
            </a>{" "}
            创建一把。开发本机也可以用环境变量 <code>DEEPSEEK_API_KEY</code> 提供。
          </p>

          {saved ? (
            <div className="keydlg-ok">
              {hasKey ? "已保存，本次会话内有效。" : "已清除。"}
            </div>
          ) : null}
        </div>

        <div className="keydlg-f">
          <button className="btn ghost" type="button" onClick={remove} disabled={!hasKey}>
            清除
          </button>
          <span className="sp" />
          <button className="btn ghost" type="button" onClick={onClose}>
            关闭
          </button>
          <button className="btn primary" type="button" onClick={save} disabled={!value.trim()}>
            保存
          </button>
        </div>
      </div>
    </>
  );
}
