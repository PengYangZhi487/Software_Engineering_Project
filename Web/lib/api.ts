/**
 * 后端 FastAPI（App/api，默认 8000）的唯一入口。
 * 服务端组件直接用 listDocuments / getParagraphs；
 * 浏览器端上传用 uploadDocument（走 multipart）。
 *
 * 换地址：在 Web/.env.local 里写 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
 */
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export interface ApiDocumentMeta {
  doc_id: number;
  project_id: number;
  filename: string;
  version: string;
  upload_time: string | null;
  paragraphs: number;
  chars: number;
  file_path: string | null;
}

export interface ApiParagraph {
  para_no: number;
  text: string;
  style: string;
  is_heading: boolean;
}

async function getJson<T>(path: string, timeoutMs = 5000): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function listDocuments(projectId = 1): Promise<ApiDocumentMeta[]> {
  const data = await getJson<{ items: ApiDocumentMeta[]; total: number }>(
    `/api/projects/${projectId}/documents`,
  );
  return data.items;
}

export async function getParagraphs(docId: number): Promise<ApiParagraph[]> {
  return getJson<ApiParagraph[]>(`/api/documents/${docId}/paragraphs`);
}

export interface UploadResult {
  document: ApiDocumentMeta;
  paragraphs: ApiParagraph[];
}

/** 后端 upload_time 是 UTC 的 "YYYY-MM-DD HH:MM:SS"，统一按东八区显示 */
export function formatApiTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value.replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

/** 浏览器端上传：docx / txt + 版本号 */
export async function uploadDocument(
  file: File,
  version: string,
  projectId = 1,
): Promise<UploadResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("version", version || "V1.0");

  const res = await fetch(`${API_BASE}/api/projects/${projectId}/documents`, {
    method: "POST",
    body,
  });

  const data = (await res.json().catch(() => null)) as
    | (UploadResult & { detail?: string })
    | null;

  if (!res.ok) {
    throw new Error(data?.detail ?? `上传失败（HTTP ${res.status}）`);
  }
  return data as UploadResult;
}
