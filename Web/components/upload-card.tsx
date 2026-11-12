"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/lib/api";
import { Icon } from "./icon";

export function UploadCard({
  onClose,
  defaultVersion = "V1.0",
}: {
  onClose?: () => void;
  defaultVersion?: string;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [version, setVersion] = useState(defaultVersion);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);

  function pick(f: File | null) {
    setError(null);
    setFile(f);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("先选一个 .docx 或 .txt 文件");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await uploadDocument(file, version);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      router.refresh();
      onClose?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card upload-card" onSubmit={submit}>
      <div className="card-h">
        <span className="t">上传文档</span>
        <span className="m">DOCX / TXT · 单文件 ≤ 10 MB</span>
      </div>

      <div className="card-b upload-body">
        <label
          className={`filedrop${drag ? " on" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            pick(e.dataTransfer.files?.[0] ?? null);
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".docx,.txt"
            hidden
            onChange={(e) => pick(e.target.files?.[0] ?? null)}
          />
          <Icon name="upload" size={16} />
          <span>
            {file ? `${file.name} · ${Math.max(1, Math.round(file.size / 1024))} KB` : "拖入 .docx / .txt，或点击选择"}
          </span>
        </label>

        <div className="upload-side">
          <label className="field">
            <span>版本号</span>
            <input value={version} maxLength={20} onChange={(e) => setVersion(e.target.value)} />
          </label>
          <div className="upload-actions">
            {onClose ? (
              <button type="button" className="btn ghost" onClick={onClose} disabled={busy}>
                取消
              </button>
            ) : null}
            <button type="submit" className="btn primary" disabled={busy}>
              {busy ? "解析中…" : "上传并解析"}
            </button>
          </div>
        </div>
      </div>

      {error ? <div className="upload-err">{error}</div> : null}
    </form>
  );
}
