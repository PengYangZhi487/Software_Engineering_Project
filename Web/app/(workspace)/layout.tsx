import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { loadDocumentCount, loadQuality, loadRequirements, loadTrace } from "@/lib/server";

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [feed, documents, quality, trace] = await Promise.all([
    loadRequirements(1),
    loadDocumentCount(1),
    loadQuality(1),
    loadTrace(1),
  ]);

  const counts = {
    documents: String(documents),
    requirements: String(feed.counts.total),
    issues: String(quality.total),
    cases: String(trace.summary.cases),
    coverage: trace.summary.confirmed ? `${trace.summary.coverage_pct}%` : "—",
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
