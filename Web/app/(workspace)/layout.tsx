import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { loadCases, loadDocumentCount, loadQuality, loadRequirements } from "@/lib/server";

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [feed, documents, quality, cases] = await Promise.all([
    loadRequirements(1),
    loadDocumentCount(1),
    loadQuality(1),
    loadCases(1),
  ]);

  const counts = {
    documents: String(documents),
    requirements: String(feed.counts.total),
    issues: String(quality.total),
    cases: String(cases.total),
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
