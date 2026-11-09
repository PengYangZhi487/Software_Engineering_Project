import { ReqExplorer } from "@/components/req-explorer";

export default async function RequirementsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; open?: string }>;
}) {
  const { q, open } = await searchParams;
  return <ReqExplorer initialQuery={q ?? ""} initialOpen={open ?? null} />;
}
