"use client";

import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { TraceBoard } from "@/components/trace-board";
import { loadTrace } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

export default function TracePage() {
  const { projectId, ready } = useCurrentProject();
  const { data, loading, error } = useApi(() => loadTrace(projectId), [projectId]);

  if (!ready || loading || !data) return <Loading title="正在读取追踪矩阵…" />;
  if (error || data.source === "mock") return <Offline message={error ?? data.error} />;

  return <TraceBoard feed={data} />;
}
