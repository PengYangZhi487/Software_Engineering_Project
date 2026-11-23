"use client";

import { useEffect, useState } from "react";
import { createRequirement, updateRequirement } from "@/lib/api";
import type { Requirement } from "@/lib/types";
import { Icon } from "./icon";

const PRIORITIES = ["高", "中", "低"];

/**
 * 需求新建 / 编辑弹窗（M2）。
 * initial 为 null 表示新建，否则编辑该需求。
 */
export function RequirementForm({
  open,
  projectId,
  initial,
  onClose,
  onSaved,
}: {
  open: boolean;
  projectId: number;
  initial: Requirement | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [reqType, setReqType] = useState("functional");
  const [priority, setPriority] = useState("中");
  const [acceptance, setAcceptance] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTitle(initial?.title ?? "");
    setDescription(initial?.desc ?? "");
    setReqType(initial?.type ?? "functional");
    setPriority(initial?.priority ?? "中");
    setAcceptance((initial?.acc ?? []).join("\n"));
    setError(null);
  }, [open, initial]);

  if (!open) return null;

  async function save() {
    const acc = acceptance
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    if (!title.trim() || !description.trim()) {
      setError("标题和描述不能为空");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        req_type: reqType,
        priority,
        acceptance: acc,
      };
      if (initial) {
        await updateRequirement(projectId, initial.id, payload);
      } else {
        await createRequirement(projectId, payload);
      }
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
      <div className="keydlg wide" role="dialog" aria-modal="true" aria-label="需求表单">
        <div className="keydlg-h">
          <Icon name={initial ? "doc" : "plus"} size={15} />
          <span className="t">{initial ? `编辑 ${initial.id}` : "新建需求"}</span>
          <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
            <Icon name="x" size={15} />
          </button>
        </div>

        <div className="keydlg-b">
          <label className="field">
            <span>标题</span>
            <input
              value={title}
              maxLength={100}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="如：退课申请审批"
            />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label className="field">
              <span>类型</span>
              <select value={reqType} onChange={(e) => setReqType(e.target.value)}>
                <option value="functional">功能需求</option>
                <option value="non_functional">非功能需求</option>
              </select>
            </label>
            <label className="field">
              <span>优先级</span>
              <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="field">
            <span>描述</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="用可验证的语言描述这条需求"
            />
          </label>

          <label className="field">
            <span>验收条件（一行一条）</span>
            <textarea
              value={acceptance}
              onChange={(e) => setAcceptance(e.target.value)}
              rows={4}
              placeholder={"审批通过后名额释放\n审批拒绝后保留名额"}
            />
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
    </>
  );
}
