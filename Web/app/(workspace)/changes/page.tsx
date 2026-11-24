"use client";

import { ChangeBoard } from "@/components/change-board";
import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { loadDiff } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

export default function ChangesPage() {
  const { projectId, ready } = useCurrentProject();
  const { data, loading, error } = useApi(() => loadDiff(projectId), [projectId]);

  if (!ready || loading || !data) {
    return <Loading title="正在比对文档版本…" hint="正在对齐两版文档的段落差异。" />;
  }
  if (error || data.source === "mock") return <Offline message={error ?? data.message} />;

  return <ChangeBoard feed={data} />;
}
