"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  importCasesXlsx,
  importRequirementsDocx,
  importRequirementsJson,
  importRequirementsXlsx,
  type ImportResult,
} from "@/lib/api";
import { Icon } from "./icon";

type Kind = "requirements" | "cases";
type Mode = "append" | "replace";

/** 导入弹窗：需求支持「上传 Excel / Word / 粘贴大模型 JSON」，用例只支持 Excel。 */
export function ImportDialog({
  open,
  kind,
  projectId,
  onClose,
  onSaved,
}: {
  open: boolean;
  kind: Kind;
  projectId: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [tab, setTab] = useState<"file" | "json">("file");
  const [mode, setMode] = useState<Mode>("append");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  useEffect(() => {
    if (!open) return;
    setTab("file");
    setMode("append");
    setFile(null);
    setText("");
    setError(null);
    setResult(null);
  }, [open]);

  if (!open) return null;

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      let res: ImportResult;
      if (kind === "requirements" && tab === "json") {
        if (!text.trim()) {
          setError("先粘贴 JSON 文本");
          return;
        }
        res = await importRequirementsJson(projectId, text, mode);
      } else {
        if (!file) {
          setError(kind === "requirements" ? "先选择一个 .xlsx 或 .docx 文件" : "先选择一个 .xlsx 文件");
          return;
        }
        if (kind === "requirements" && /\.docx$/i.test(file.name)) {
          res = await importRequirementsDocx(projectId, file, mode);
        } else {
          res =
            kind === "requirements"
              ? await importRequirementsXlsx(projectId, file, mode)
              : await importCasesXlsx(projectId, file);
        }
      }
      setResult(res);
      if (res.created + res.updated > 0) onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <>
      <div className="scrim on" onClick={onClose} />
      <div className="keydlg wide" role="dialog" aria-modal="true" aria-label="导入">
        <div className="keydlg-h">
          <Icon name="upload" size={15} />
          <span className="t">{kind === "requirements" ? "导入需求" : "导入用例"}</span>
          <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
            <Icon name="x" size={15} />
          </button>
        </div>

        <div className="keydlg-b">
          {kind === "requirements" ? (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className={`btn sm ${tab === "file" ? "primary" : "ghost"}`}
                type="button"
                onClick={() => setTab("file")}
              >
                上传 Excel / Word
              </button>
              <button
                className={`btn sm ${tab === "json" ? "primary" : "ghost"}`}
                type="button"
                onClick={() => setTab("json")}
              >
                粘贴大模型输出
              </button>
            </div>
          ) : null}

          {kind === "requirements" && tab === "json" ? (
            <label className="field">
              <span>
                粘贴 JSON（{"{requirements: [...]}"} 或数组；模型给的编号会被忽略，由程序续号）
              </span>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                placeholder='{"requirements":[{"title":"...","description":"...","acceptance_criteria":["..."]}]}'
              />
            </label>
          ) : (
            <label className="field">
              <span>
                {kind === "requirements"
                  ? "选择 .xlsx 或 .docx（Excel 当编辑器改完再导入，或直接导入 Word 需求表）"
                  : "选择 .xlsx（建议先点「导出」，在 Excel 里改完再导入）"}
              </span>
              <input
                type="file"
                accept={kind === "requirements" ? ".xlsx,.docx" : ".xlsx"}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{file.name}</div>
              ) : null}
            </label>
          )}

          {kind === "requirements" ? (
            <div style={{ display: "flex", gap: 14, alignItems: "center", fontSize: 12 }}>
              <span style={{ color: "var(--text-2)" }}>导入方式</span>
              <label style={{ display: "flex", gap: 5, alignItems: "center" }}>
                <input type="radio" checked={mode === "append"} onChange={() => setMode("append")} />
                追加（保留已有）
              </label>
              <label style={{ display: "flex", gap: 5, alignItems: "center" }}>
                <input type="radio" checked={mode === "replace"} onChange={() => setMode("replace")} />
                覆盖（先清空）
              </label>
            </div>
          ) : null}

          {kind === "requirements" && mode === "replace" ? (
            <div className="extract-status error">
              覆盖导入会先清空当前项目的需求、用例与执行记录，请确认后再导入。
            </div>
          ) : null}

          {error ? (
            <div className="upload-err" style={{ padding: 0 }}>
              {error}
            </div>
          ) : null}

          {result ? (
            <div className="extract-status ok" style={{ display: "block", whiteSpace: "pre-wrap" }}>
              新增 {result.created} 条，更新 {result.updated} 条，跳过 {result.skipped} 条
              {result.errors.length ? `\n${result.errors.join("\n")}` : ""}
            </div>
          ) : null}
        </div>

        <div className="keydlg-f">
          <span className="sp" />
          <button className="btn ghost" type="button" onClick={onClose} disabled={busy}>
            关闭
          </button>
          <button className="btn primary" type="button" onClick={run} disabled={busy}>
            {busy ? "导入中…" : "开始导入"}
          </button>
        </div>
      </div>
    </>,
    document.body,
  );
}
