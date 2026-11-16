import { CaseBoard } from "@/components/case-board";
import { loadCases, loadRequirements } from "@/lib/server";

export const metadata = { title: "测试用例 · RATGP" };

export default async function CasesPage() {
  const [feed, requirements] = await Promise.all([loadCases(1), loadRequirements(1)]);

  return <CaseBoard feed={feed} requirements={requirements.items} />;
}
