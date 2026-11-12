import { ReqExplorer } from "@/components/req-explorer";
import { loadRequirements } from "@/lib/server";

export default async function RequirementsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; open?: string }>;
}) {
  const { q, open } = await searchParams;
  const feed = await loadRequirements(1);

  return (
    <ReqExplorer
      items={feed.items}
      source={feed.source}
      initialQuery={q ?? ""}
      initialOpen={open ?? null}
    />
  );
}
