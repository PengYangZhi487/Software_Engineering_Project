import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { loadDocumentCount, loadRequirements } from "@/lib/server";

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [feed, documents] = await Promise.all([loadRequirements(1), loadDocumentCount(1)]);

  const counts = {
    documents: String(documents),
    requirements: String(feed.counts.total),
    issues: String(feed.counts.ambiguous),
    cases: "0",
    coverage: "—",
  };

  return (
    <div className="app">
      <Sidebar counts={counts} />
      <div className="main">
        <Topbar />
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
