"use client";

import { useEffect, useState } from "react";
import { createExecution, type ExecutionPayload } from "@/lib/api";
import type { TestCaseItem } from "@/lib/server";
import { Icon } from "./icon";

const RESULTS: { id: ExecutionPayload["result"]; label: string }[] = [
  { id: "pass", label: "通过" },
  { id: "fail", label: "失败" },
  { id: "blocked", label: "阻塞" },
];

/** 执行记录弹窗：补上「生成 ≠ 执行 ≠ 通过」的最后一环。 */
export function ExecutionForm({
  open,
  projectId,
  testCase,
  onClose,
  onSaved,
}: {
  open: boolean;
  projectId: number;
  testCase: TestCaseItem | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [result, setResult] = useState<ExecutionPayload["result"]>("pass");
  const [actual, setActual] = useState("");
  const [comments, setComments] = useState("");
  const [tester, setTester] = useState("");
  const [signature, setSignature] = useState("");
  const [environment, setEnvironment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setResult("pass");
    setActual("");
    setComments("");
    setTester("");
    setSignature("");
    setEnvironment("");
    setError(null);
  }, [open]);

  if (!open || !testCase) return null;

  async function save() {
    if (!testCase) return;
    setBusy(true);
    setError(null);
    try {
      await createExecution(projectId, {
        tc_id: testCase.tc_id,
        result,
        actual_result: actual.trim() || undefined,
        comments: comments.trim() || undefined,
        tester: tester.trim() || undefined,
        signature: signature.trim() || undefined,
        environment: environment.trim() || undefined,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="scrim on" onClick={onClose} />
      <div className="keydlg wide" role="dialog" aria-modal="true" aria-label="记录执行">
        <div className="keydlg-h">
          <Icon name="flask" size={15} />
          <span className="t">记录执行 · TC-{String(testCase.tc_id).padStart(3, "0")}</span>
          <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
            <Icon name="x" size={15} />
          </button>
        </div>

        <div className="keydlg-b">
          <div className="field">
            <span>用例</span>
            <div style={{ fontSize: 12.5, fontWeight: 550 }}>{testCase.title}</div>
            <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>
              预期：{testCase.expected_result}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label className="field">
              <span>执行结果</span>
              <select
                value={result}
                onChange={(e) => setResult(e.target.value as ExecutionPayload["result"])}
              >
                {RESULTS.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>执行环境</span>
              <input
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                placeholder="Windows 11 / Chrome 141"
              />
            </label>
          </div>

          <label className="field">
            <span>实际结果</span>
            <textarea
              value={actual}
              onChange={(e) => setActual(e.target.value)}
              rows={2}
              placeholder="实际看到的现象，与预期是否一致"
            />
          </label>

          <label className="field">
            <span>测试 comments</span>
            <textarea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              rows={2}
              placeholder="备注、缺陷编号、复现条件等"
            />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label className="field">
              <span>执行人</span>
              <input value={tester} onChange={(e) => setTester(e.target.value)} placeholder="姓名" />
            </label>
            <label className="field">
              <span>测试者签名</span>
              <input
                value={signature}
                onChange={(e) => setSignature(e.target.value)}
                placeholder="签名 / 拼音缩写"
              />
            </label>
          </div>

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
            {busy ? "保存中…" : "保存执行记录"}
          </button>
        </div>
      </div>
    </>
  );
}
