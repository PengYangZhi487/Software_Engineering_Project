"use client";

import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { QualityBoard } from "@/components/quality-board";
import { loadQuality } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

export default function QualityPage() {
  const { projectId, ready } = useCurrentProject();
  const { data, loading, error } = useApi(() => loadQuality(projectId), [projectId]);

  if (!ready || loading || !data) return <Loading title="正在读取质量问题…" />;
  if (error || data.source === "mock") return <Offline message={error ?? data.error} />;

  return <QualityBoard feed={data} />;
}
