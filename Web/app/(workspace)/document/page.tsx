import { DocWorkspace } from "@/components/doc-workspace";
import {
  getParagraphs,
  listDocuments,
  type ApiDocumentMeta,
  type ApiParagraph,
} from "@/lib/api";

export const metadata = { title: "文档工作台 · RATGP" };

export default async function DocumentPage({
  searchParams,
}: {
  searchParams: Promise<{ upload?: string }>;
}) {
  const { upload } = await searchParams;

  let doc: ApiDocumentMeta | null = null;
  let paragraphs: ApiParagraph[] = [];
  let apiError: string | null = null;

  try {
    const docs = await listDocuments(1);
    doc = docs[0] ?? null;
    if (doc) paragraphs = await getParagraphs(doc.doc_id);
  } catch (err) {
    apiError = err instanceof Error ? err.message : "无法连接后端";
  }

  return (
    <DocWorkspace
      doc={doc}
      paragraphs={paragraphs}
      apiError={apiError}
      initialUploadOpen={upload === "1"}
    />
  );
}
