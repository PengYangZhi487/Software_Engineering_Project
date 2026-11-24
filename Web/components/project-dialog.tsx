"use client";

/**
 * 项目弹窗：新建 / 重命名 / 删除（多项目）。
 *
 * - 新建：POST /api/projects（名称空白后端 422，前端先拦一次）
 * - 重命名：PATCH /api/projects/{id}（只发改动字段；description 为空即清空）
 * - 删除：DELETE 默认 force=false；后端有需求/文档时返回 409，弹窗切成「强制删除」
 *   二次确认（force=true），成功后由调用方切到别的项目，不停留在已删除的项目上。
 */
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  ApiError,
  createProject,
  deleteProject,
  updateProject,
  type ApiProject,
} from "@/lib/api";
import { Icon } from "./icon";

export type ProjectDialogMode = "create" | "rename" | "delete";

export function ProjectDialog({
  open,
  mode,
  project,
  onClose,
  onSaved,
}: {
  open: boolean;
  mode: ProjectDialogMode;
  project: ApiProject | null;
  onClose: () => void;
  onSaved: (action: "created" | "renamed" | "deleted", project: ApiProject | null) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(project?.project_name ?? "");
    setDescription(project?.description ?? "");
    setForce(false);
    setBusy(false);
    setError(null);
  }, [open, project]);

  if (!open) return null;

  const isDelete = mode === "delete";
  const title = mode === "create" ? "新建项目" : mode === "rename" ? "重命名项目" : "删除项目";

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      if (isDelete) {
        if (!project) {
          setError("没有可删除的项目");
          return;
        }
        await deleteProject(project.project_id, force);
        onSaved("deleted", null);
        onClose();
        return;
      }

      const trimmed = name.trim();
      if (!trimmed) {
        setError("项目名称不能为空");
        return;
      }
      const desc = description.trim() || null;

      if (mode === "create") {
        const created = await createProject({ project_name: trimmed, description: desc });
        onSaved("created", created);
      } else if (project) {
        const updated = await updateProject(project.project_id, {
          project_name: trimmed,
          description: desc,
        });
        onSaved("renamed", updated);
      }
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setForce(true);
        setError(
          `${err.message}。再次点击「强制删除」会连同需求、文档、用例与执行记录一起清空，且不可恢复。`,
        );
      } else if (err instanceof ApiError && err.status === 404) {
        setError("项目不存在，可能已被删除；刷新后再试。");
      } else {
        setError(err instanceof Error ? err.message : "操作失败");
      }
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <>
      <div className="scrim on" onClick={onClose} />
      <div className="keydlg" role="dialog" aria-modal="true" aria-label={title}>
        <div className="keydlg-h">
          <Icon name={isDelete ? "alert" : "flow"} size={15} />
          <span className="t">{title}</span>
          <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
            <Icon name="x" size={15} />
          </button>
        </div>

        <div className="keydlg-b">
          {isDelete ? (
            <>
              <p style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.8 }}>
                确定删除项目「<b style={{ color: "var(--text)" }}>{project?.project_name ?? "—"}</b>」？
                项目下还有需求或文档时，后端会先拦一次（409），确认后才会连同需求、文档、用例、
                执行记录一起清理。磁盘上的原始上传文件不会删除。
              </p>
              {force ? (
                <div className="extract-status error">
                  这是强制删除：该项目下的全部业务数据会被清空，无法恢复。
                </div>
              ) : null}
            </>
          ) : (
            <>
              <label className="field">
                <span>项目名称</span>
                <input
                  value={name}
                  maxLength={60}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例如：校园选课系统"
                  autoFocus
                />
              </label>
              <label className="field">
                <span>项目描述（可选）</span>
                <textarea
                  value={description}
                  rows={3}
                  maxLength={500}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="一句话说明这个项目做什么"
                />
              </label>
            </>
          )}

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
          <button
            className={`btn ${isDelete ? "danger" : "primary"}`}
            type="button"
            onClick={submit}
            disabled={busy}
          >
            {busy
              ? "处理中…"
              : isDelete
                ? force
                  ? "强制删除"
                  : "删除"
                : mode === "create"
                  ? "创建项目"
                  : "保存修改"}
          </button>
        </div>
      </div>
    </>,
    document.body,
  );
}
