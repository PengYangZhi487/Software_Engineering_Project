"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { updateCase } from "@/lib/api";
import type { TestCaseItem } from "@/lib/server";
import { Icon } from "./icon";

const TYPES = [
  { id: "normal", label: "正常" },
  { id: "abnormal", label: "异常" },
  { id: "boundary", label: "边界" },
];
const STATUSES = ["已生成", "已审核", "已驳回", "已执行"];

const splitLines = (text: string) =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

/** 用例编辑弹窗（M4）。 */
export function CaseForm({
  open,
  projectId,
  initial,
  onClose,
  onSaved,
}: {
  open: boolean;
  projectId: number;
  initial: TestCaseItem | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [steps, setSteps] = useState("");
  const [expected, setExpected] = useState("");
  const [testType, setTestType] = useState("normal");
  const [status, setStatus] = useState("已生成");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !initial) return;
    setTitle(initial.title);
    setPreconditions(initial.preconditions.join("\n"));
    setSteps(initial.steps.join("\n"));
    setExpected(initial.expected_result);
    setTestType(initial.test_type);
    setStatus(initial.status);
    setError(null);
  }, [open, initial]);

  if (!open || !initial) return null;

  async function save() {
    if (!initial) return;
    if (!title.trim() || !expected.trim()) {
      setError("标题和预期结果不能为空");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateCase(projectId, initial.tc_id, {
        title: title.trim(),
        preconditions: splitLines(preconditions),
        steps: splitLines(steps),
        expected_result: expected.trim(),
        test_type: testType,
        status,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <>
      <div className="scrim on" onClick={onClose} />
      <div className="keydlg wide" role="dialog" aria-modal="true" aria-label="用例表单">
        <div className="keydlg-h">
          <Icon name="flask" size={15} />
          <span className="t">编辑 TC-{String(initial.tc_id).padStart(3, "0")}</span>
          <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
            <Icon name="x" size={15} />
          </button>
        </div>

        <div className="keydlg-b">
          <label className="field">
            <span>标题</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label className="field">
              <span>类型</span>
              <select value={testType} onChange={(e) => setTestType(e.target.value)}>
                {TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>状态</span>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="field">
            <span>前置条件（一行一条）</span>
            <textarea
              value={preconditions}
              onChange={(e) => setPreconditions(e.target.value)}
              rows={2}
            />
          </label>

          <label className="field">
            <span>操作步骤（一行一步）</span>
            <textarea value={steps} onChange={(e) => setSteps(e.target.value)} rows={3} />
          </label>

          <label className="field">
            <span>预期结果</span>
            <textarea value={expected} onChange={(e) => setExpected(e.target.value)} rows={2} />
          </label>

          {error ? (
            <div className="upload-err" style={{ padding: 0 }}>
              {error}
            </div>
          ) : null}
        </div>

        <div className="keydlg-f">
          <span className="sp" />
          <button className="btn ghost" type="button" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button className="btn primary" type="button" onClick={save} disabled={busy}>
            {busy ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </>,
    document.body,
  );
}
