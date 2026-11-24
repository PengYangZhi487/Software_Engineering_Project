"use client";

/**
 * 工作台外壳：侧栏（项目选择器 + 数字）+ 顶栏 + 页面内容。
 *
 * 多项目：
 * - 当前项目来自 lib/project.ts（URL ?project= > localStorage > 1）；
 * - 侧栏项目下拉取 GET /api/projects，新建/重命名/删除走项目 CRUD；
 * - 切换项目后所有 useApi 依赖 projectId 自动重取，侧栏数字、页面数据一起变；
 * - 删除当前项目后切到剩余第一个；一个都不剩就新建一个默认项目，不停留在已删除项目上。
 */
import { useState, type ReactNode } from "react";
import { LockGate } from "@/components/lock-gate";
import { ProjectDialog, type ProjectDialogMode } from "@/components/project-dialog";
import { Sidebar, type SidebarCounts } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { createProject, type ApiProject } from "@/lib/api";
import {
  loadDiff,
  loadDocumentCount,
  loadProjects,
  loadQuality,
  loadRequirements,
  loadTrace,
} from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { notifyDataChanged, useApi } from "@/lib/use-api";

const EMPTY_COUNTS: SidebarCounts = {
  documents: "—",
  requirements: "—",
  issues: "—",
  cases: "—",
  coverage: "—",
  changes: "—",
};

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  // 本地锁：未解锁时只渲染锁屏，WorkspaceShell 不挂载（也就不会去取业务数据）
  return (
    <LockGate>
      <WorkspaceShell>{children}</WorkspaceShell>
    </LockGate>
  );
}

function WorkspaceShell({ children }: { children: ReactNode }) {
  const { projectId, setProjectId } = useCurrentProject();

  // 项目列表：新建/改名/删除后由 notifyDataChanged() 触发重取
  const projectsApi = useApi(() => loadProjects());
  const projects = projectsApi.data ?? [];
  const current = projects.find((project) => project.project_id === projectId) ?? null;

  // 侧栏数字：跟着当前项目走
  const { data } = useApi(async () => {
    const [feed, documents, quality, trace, diff] = await Promise.all([
      loadRequirements(projectId),
      loadDocumentCount(projectId),
      loadQuality(projectId),
      loadTrace(projectId),
      loadDiff(projectId),
    ]);
    return { feed, documents, quality, trace, diff };
  }, [projectId]);

  const [dialog, setDialog] = useState<{ mode: ProjectDialogMode; project: ApiProject | null } | null>(
    null,
  );

  const counts: SidebarCounts = data
    ? {
        documents: String(data.documents),
        requirements: String(data.feed.counts.total),
        issues: String(data.quality.total),
        cases: String(data.trace.summary.cases),
        coverage: data.trace.summary.confirmed ? `${data.trace.summary.coverage_pct}%` : "—",
        changes: data.diff.available ? String(data.diff.data?.summary.changed ?? 0) : "—",
      }
    : EMPTY_COUNTS;

  async function handleSaved(
    action: "created" | "renamed" | "deleted",
    project: ApiProject | null,
  ) {
    // 项目增删改后刷新项目列表与所有页面数据
    notifyDataChanged();

    if (action === "created" && project) {
      setProjectId(project.project_id);
      return;
    }

    if (action === "deleted") {
      const remaining = projects.filter((item) => item.project_id !== projectId);
      if (remaining.length > 0) {
        setProjectId(remaining[0].project_id);
        return;
      }
      // 一个项目都不剩：建一个默认项目，避免停在已删除项目的数据上
      try {
        const created = await createProject({ project_name: "我的项目", description: null });
        notifyDataChanged();
        setProjectId(created.project_id);
      } catch {
        /* 建不成就保持现状，页面会显示离线态 */
      }
    }
  }

  return (
    <div className="app">
      <Sidebar
        counts={counts}
        projects={projects}
        currentProjectId={projectId}
        currentProjectName={current?.project_name ?? null}
        onSelectProject={(id) => setProjectId(id)}
        onCreateProject={() => setDialog({ mode: "create", project: null })}
        onRenameProject={() => setDialog(current ? { mode: "rename", project: current } : null)}
        onDeleteProject={() => setDialog(current ? { mode: "delete", project: current } : null)}
      />
      <div className="main">
        <Topbar projectName={current?.project_name ?? null} />
        {/* key=projectId：切换项目时整棵页面重新挂载，清掉跨项目的选中/抽屉等临时状态 */}
        <div className="content" key={projectId}>
          {children}
        </div>
      </div>

      <ProjectDialog
        open={dialog !== null}
        mode={dialog?.mode ?? "create"}
        project={dialog?.project ?? null}
        onClose={() => setDialog(null)}
        onSaved={handleSaved}
      />
    </div>
  );
}
