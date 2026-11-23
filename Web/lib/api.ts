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
}

export interface ApiParagraph {
  para_no: number;
  text: string;
  style: string;
  is_heading: boolean;
}

/* ---------- DeepSeek API Key（BYOK） ---------- */

const KEY_STORAGE = "ratgp-deepseek-key";

/** 读当前会话的 key；服务端渲染时恒为 null。 */
export function getApiKey(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(KEY_STORAGE) || null;
  } catch {
    return null;
  }
}

/** 写入 key（只进 sessionStorage：刷新还在，关标签页失效）。 */
export function setApiKey(key: string): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(KEY_STORAGE, key.trim());
    window.dispatchEvent(new Event("ratgp-key-changed"));
  } catch {
    /* 隐私模式/存储被禁用时忽略 */
  }
}

export function clearApiKey(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(KEY_STORAGE);
    window.dispatchEvent(new Event("ratgp-key-changed"));
  } catch {
    /* ignore */
  }
}

/** 带 HTTP 状态码的 API 错误，401 由调用方引导去设置 key。 */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * 后端请求的唯一入口：自动带 X-DeepSeek-Key，非 2xx 抛 ApiError。
 * 没有 key 时也放行——只有真正调大模型的接口会返回 401。
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const key = getApiKey();
  if (key) headers.set("X-DeepSeek-Key", key);
  if (typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init, headers });

  if (!res.ok) {
    const data = (await res.json().catch(() => null)) as { detail?: string } | null;
    const message =
      res.status === 401
        ? "缺少 DeepSeek API Key：请点右上角「设置」填入"
        : data?.detail ?? `API ${res.status} ${res.statusText}`;
    throw new ApiError(message, res.status);
  }
  return res;
}

async function getJson<T>(path: string, timeoutMs = 5000): Promise<T> {
  const res = await apiFetch(path, { signal: AbortSignal.timeout(timeoutMs) });
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

/** 浏览器端上传：docx / txt + 版本号（上传不调大模型，不需要 key） */
export async function uploadDocument(
  file: File,
  version: string,
  projectId = 1,
): Promise<UploadResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("version", version || "V1.0");

  const res = await apiFetch(`/api/projects/${projectId}/documents`, {
    method: "POST",
    body,
  });
  return (await res.json()) as UploadResult;
}

/* ---------- 需求写操作（M2） ---------- */

export interface RequirementPayload {
  title: string;
  description: string;
  req_type: string;
  priority: string;
  acceptance: string[];
}

export async function createRequirement(
  projectId: number,
  payload: RequirementPayload,
): Promise<void> {
  await apiFetch(`/api/projects/${projectId}/requirements`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRequirement(
  projectId: number,
  reqId: string,
  payload: Partial<RequirementPayload> & { status?: string },
): Promise<void> {
  await apiFetch(`/api/projects/${projectId}/requirements/${reqId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/* ---------- 用例写操作（M4） ---------- */

export interface CasePayload {
  title?: string;
  preconditions?: string[];
  steps?: string[];
  expected_result?: string;
  test_type?: string;
  status?: string;
}

export async function updateCase(
  projectId: number,
  tcId: number,
  payload: CasePayload,
): Promise<void> {
  await apiFetch(`/api/projects/${projectId}/cases/${tcId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/* ---------- 质量裁决（M3） ---------- */

export async function decideQualityIssue(
  projectId: number,
  fingerprint: string,
  decision: "open" | "confirmed" | "ignored",
  note?: string,
): Promise<void> {
  await apiFetch(`/api/projects/${projectId}/quality/issues/${fingerprint}`, {
    method: "PATCH",
    body: JSON.stringify({ decision, note }),
  });
}

/* ---------- 执行记录 ---------- */

export interface ExecutionPayload {
  tc_id: number;
  result: "pass" | "fail" | "blocked";
  actual_result?: string;
  comments?: string;
  tester?: string;
  signature?: string;
  environment?: string;
}

export async function createExecution(projectId: number, payload: ExecutionPayload): Promise<void> {
  await apiFetch(`/api/projects/${projectId}/executions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/* ---------- 用例批量审核 ---------- */

export async function batchUpdateCases(
  projectId: number,
  tcIds: number[],
  status: string,
): Promise<number> {
  const res = await apiFetch(`/api/projects/${projectId}/cases/batch`, {
    method: "PATCH",
    body: JSON.stringify({ tc_ids: tcIds, status }),
  });
  const data = (await res.json()) as { updated?: number };
  return data.updated ?? 0;
}

/** 报告导出地址（浏览器直接下载，不经过 fetch）。 */
export function exportReportUrl(projectId: number, format: "csv" | "xlsx" = "xlsx"): string {
  return `${API_BASE}/api/projects/${projectId}/report/export?format=${format}`;
}
