import { CaseBoard } from "@/components/case-board";
import { Offline } from "@/components/offline";
import { loadCases, loadExecutions, loadRequirements } from "@/lib/server";

export const metadata = { title: "测试用例 · RATGP" };

export default async function CasesPage() {
  const [feed, requirements, executions] = await Promise.all([
    loadCases(1),
    loadRequirements(1),
    loadExecutions(1),
  ]);
  if (feed.source === "mock" || requirements.source === "mock") {
    return <Offline message={feed.error ?? requirements.error} />;
  }

  return <CaseBoard feed={feed} requirements={requirements.items} executions={executions.items} />;
}
