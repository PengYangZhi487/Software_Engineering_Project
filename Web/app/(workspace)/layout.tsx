import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import {
  loadDiff,
  loadDocumentCount,
  loadQuality,
  loadRequirements,
  loadTrace,
} from "@/lib/server";

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [feed, documents, quality, trace, diff] = await Promise.all([
    loadRequirements(1),
    loadDocumentCount(1),
    loadQuality(1),
    loadTrace(1),
    loadDiff(1),
  ]);

  const counts = {
    documents: String(documents),
    requirements: String(feed.counts.total),
    issues: String(quality.total),
    cases: String(trace.summary.cases),
    coverage: trace.summary.confirmed ? `${trace.summary.coverage_pct}%` : "—",
    changes: diff.available ? String(diff.data?.summary.changed ?? 0) : "—",
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
