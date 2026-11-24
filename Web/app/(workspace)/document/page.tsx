"use client";

import { DocWorkspace } from "@/components/doc-workspace";
import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { loadDocumentWorkspace } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi, useQueryFlag } from "@/lib/use-api";

/**
 * 文档工作台：文档、段落、需求全部在浏览器里取，跟随当前项目。
 * ?upload=1 / ?extract=1 是链接直达时自动展开对应面板的一次性开关。
 */
export default function DocumentPage() {
  const { projectId, ready } = useCurrentProject();
  const uploadOpen = useQueryFlag("upload");
  const extractOpen = useQueryFlag("extract");
  const { data, loading, error } = useApi(() => loadDocumentWorkspace(projectId), [projectId]);

  if (!ready || loading || !data) {
    return <Loading title="正在读取文档…" hint="正在加载最新文档与段落。" />;
  }
  if (error) return <Offline message={error} />;

  return (
    <DocWorkspace
      doc={data.doc}
      paragraphs={data.paragraphs}
      apiError={null}
      requirements={data.requirements}
      initialUploadOpen={uploadOpen}
      initialExtractOpen={extractOpen}
    />
  );
}
