/**
 * 后端 FastAPI（App/api）的唯一入口，全部请求都在浏览器里发出。
 *
 * 地址规则：
 * - 生产（next build → 静态导出，桌面壳里由 Python 同源托管）：相对路径 /api/...，不依赖端口；
 * - 开发（next dev，前端在 3000）：默认打到 http://127.0.0.1:8000；
 * - 需要别的地址：设 NEXT_PUBLIC_API_BASE（覆盖上面两条）。
 */
const ENV_API_BASE = process.env.NEXT_PUBLIC_API_BASE;
const DEV_API_BASE = process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "";

export const API_BASE = (ENV_API_BASE ?? DEV_API_BASE).replace(/\/$/, "");

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

export async function listDocuments(projectId: number): Promise<ApiDocumentMeta[]> {
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
  projectId: number,
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

/* ---------- 导入 / 导出（Excel 当编辑器） ---------- */

export interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export async function importRequirementsXlsx(
  projectId: number,
  file: File,
  mode: "append" | "replace",
): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("mode", mode);
  const res = await apiFetch(`/api/projects/${projectId}/requirements/import/xlsx`, {
    method: "POST",
    body,
  });
  return (await res.json()) as ImportResult;
}

export async function importRequirementsJson(
  projectId: number,
  text: string,
  mode: "append" | "replace",
): Promise<ImportResult> {
  const res = await apiFetch(`/api/projects/${projectId}/requirements/import/json`, {
    method: "POST",
    body: JSON.stringify({ mode, text }),
  });
  return (await res.json()) as ImportResult;
}

/** Word 需求表导入（后端解析 .docx 表格，响应与 xlsx 相同）。 */
export async function importRequirementsDocx(
  projectId: number,
  file: File,
  mode: "append" | "replace",
): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("mode", mode);
  const res = await apiFetch(`/api/projects/${projectId}/requirements/import/docx`, {
    method: "POST",
    body,
  });
  return (await res.json()) as ImportResult;
}

export async function importCasesXlsx(projectId: number, file: File): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  const res = await apiFetch(`/api/projects/${projectId}/cases/import/xlsx`, {
    method: "POST",
    body,
  });
  return (await res.json()) as ImportResult;
}

export function exportRequirementsUrl(projectId: number): string {
  return `${API_BASE}/api/projects/${projectId}/requirements/export?format=xlsx`;
}

export function exportCasesUrl(projectId: number): string {
  return `${API_BASE}/api/projects/${projectId}/cases/export?format=xlsx`;
}

/* ---------- 项目（多项目：新建 / 重命名 / 删除） ---------- */

export interface ApiProject {
  project_id: number;
  project_name: string;
  description: string | null;
  /** 该项目下的需求条数（列表接口带上，侧栏用） */
  req_count: number;
}

export interface ProjectDeleteResult {
  deleted: boolean;
  project_id: number;
  project_name: string;
  requirements: number;
  documents: number;
  cases: number;
  executions: number;
}

export async function createProject(payload: {
  project_name: string;
  description?: string | null;
}): Promise<ApiProject> {
  const res = await apiFetch("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return (await res.json()) as ApiProject;
}

/** 只提交显式给出的字段（description 传 null 表示清空）。 */
export async function updateProject(
  projectId: number,
  payload: { project_name?: string; description?: string | null },
): Promise<ApiProject> {
  const res = await apiFetch(`/api/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return (await res.json()) as ApiProject;
}

/**
 * 删除项目。默认 force=false：有需求/文档时后端返回 409（ApiError），
 * 调用方确认后带 force=true 重发才会级联清理。
 */
export async function deleteProject(
  projectId: number,
  force = false,
): Promise<ProjectDeleteResult> {
  const res = await apiFetch(
    `/api/projects/${projectId}${force ? "?force=true" : ""}`,
    { method: "DELETE" },
  );
  return (await res.json()) as ProjectDeleteResult;
}

/* ---------- 本地锁（桌面软件的门禁，不是网络级鉴权） ---------- */

export interface AuthStatus {
  /** 是否设置过本地锁密码 */
  configured: boolean;
  /** 当前是否需要输入密码（未设置时恒为 false） */
  locked: boolean;
  token_ttl_seconds: number;
}

export interface AuthLoginResult {
  token: string;
  expires_in: number;
  configured: boolean;
  locked: boolean;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const res = await apiFetch("/api/auth/status");
  return (await res.json()) as AuthStatus;
}

/** 首次设置密码：成功 201，密码不足 4 位 422，已设置过 409。 */
export async function setupLockPassword(password: string): Promise<AuthStatus> {
  const res = await apiFetch("/api/auth/setup", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  return (await res.json()) as AuthStatus;
}

/** 登录：密码错 401，还没设置密码 409。 */
export async function loginLock(password: string): Promise<AuthLoginResult> {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  return (await res.json()) as AuthLoginResult;
}

/** 锁定：后端清空内存 token，之后需要重新登录。 */
export async function lockApp(): Promise<AuthStatus> {
  const res = await apiFetch("/api/auth/lock", { method: "POST" });
  return (await res.json()) as AuthStatus;
}

/* ---------- 导出到本地数据目录（桌面版下载不可靠时使用） ---------- */

export interface SavedExport {
  path: string;
  filename: string;
  size: number;
}

/** 让后端生成文件并保存到 <数据目录>/exports/，返回绝对路径。 */
export async function saveExportFile(
  projectId: number,
  kind: "report" | "requirements" | "cases",
  format: "xlsx" | "csv" = "xlsx",
): Promise<SavedExport> {
  const res = await apiFetch(`/api/projects/${projectId}/export-file`, {
    method: "POST",
    body: JSON.stringify({ kind, format }),
  });
  return (await res.json()) as SavedExport;
}
