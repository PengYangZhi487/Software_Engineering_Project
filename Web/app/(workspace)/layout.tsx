import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <Sidebar />
      <div className="main">
        <Topbar />
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
