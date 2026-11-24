"use client";

import { ReqExplorer } from "@/components/req-explorer";
import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { loadRequirements } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

export default function RequirementsPage() {
  const { projectId, ready } = useCurrentProject();
  const { data, loading, error } = useApi(() => loadRequirements(projectId), [projectId]);

  // ?q= / ?open= 由 ReqExplorer 自己从地址栏读（静态导出没有 searchParams）
  if (!ready || loading || !data) return <Loading title="正在读取需求库…" />;
  if (error || data.source === "mock") return <Offline message={error ?? data.error} />;

  return <ReqExplorer items={data.items} source={data.source} />;
}
