"use client";

import { CaseBoard } from "@/components/case-board";
import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { loadCases, loadExecutions, loadRequirements } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

export default function CasesPage() {
  const { projectId, ready } = useCurrentProject();
  const { data, loading, error } = useApi(async () => {
    const [feed, requirements, executions] = await Promise.all([
      loadCases(projectId),
      loadRequirements(projectId),
      loadExecutions(projectId),
    ]);
    return { feed, requirements, executions };
  }, [projectId]);

  if (!ready || loading || !data) return <Loading title="正在读取测试用例…" />;
  if (error || data.feed.source === "mock" || data.requirements.source === "mock") {
    return <Offline message={error ?? data.feed.error ?? data.requirements.error} />;
  }

  return (
    <CaseBoard
      feed={data.feed}
      requirements={data.requirements.items}
      executions={data.executions.items}
    />
  );
}
