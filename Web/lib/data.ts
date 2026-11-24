/**
 * 客户端数据入口：页面与组件在浏览器里直接 fetch FastAPI。
 *
 * 静态导出（next.config.ts 的 output: "export"）之后没有 Node 服务端可以取数，
 * 所以原来 lib/server.ts 的 load* 全部搬到这里并改成浏览器 fetch：
 * - API_BASE 为空时走同源相对路径（桌面壳由 Python 一并托管）；
 * - 失败不抛异常，返回 source: "mock" + error 的结构，由页面统一渲染 <Offline />；
 * - 写操作成功后调 notifyDataChanged()（lib/use-api.ts），所有 useApi 自动重新取数。
 */
import {
  ApiError,
  apiFetch,
  getParagraphs,
  listDocuments,
  type ApiDocumentMeta,
  type ApiParagraph,
  type ApiProject,
} from "./api";
import type { DataSource, Requirement, Risk } from "./types";

interface ApiRequirement {
  req_id: string;
  project_id: number;
  title: string;
  description: string;
  req_type: string;
  priority: string;
  status: string;
  acceptance: string[];
  source_location: { para_no?: number | null; raw?: string | null; ratio?: number | null } | null;
  is_ambiguous: boolean;
}

interface ApiRequirementList {
  items: ApiRequirement[];
  total: number;
  confirmed: number;
  ambiguous: number;
}

const STATUS_MAP: Record<string, Requirement["status"]> = {
  已确认: "confirmed",
  已驳回: "rejected",
  未审核: "unconfirmed",
};

export interface RequirementCounts {
  total: number;
  confirmed: number;
  rejected: number;
  pending: number;
  ambiguous: number;
}

export interface RequirementFeed {
  items: Requirement[];
  source: DataSource;
  error: string | null;
  counts: RequirementCounts;
}

export function countRequirements(items: Requirement[]): RequirementCounts {
  return {
    total: items.length,
    confirmed: items.filter((r) => r.status === "confirmed").length,
    rejected: items.filter((r) => r.status === "rejected").length,
    pending: items.filter((r) => r.status === "unconfirmed").length,
    ambiguous: items.filter((r) => r.risks.includes("ambiguous")).length,
  };
}

function toRequirement(row: ApiRequirement): Requirement {
  const loc = row.source_location ?? {};
  const risks: Risk[] = row.is_ambiguous ? ["ambiguous"] : [];
  return {
    id: row.req_id,
    project_id: row.project_id,
    title: row.title,
    desc: row.description,
    type: row.req_type === "non_functional" ? "non_functional" : "functional",
    priority: row.priority ?? "中",
    acc: row.acceptance ?? [],
    risks,
    status: STATUS_MAP[row.status] ?? "unconfirmed",
    para: loc.para_no ?? 0,
    ratio: loc.ratio ?? 0,
    raw: loc.raw ?? "",
    covered: false,
  };
}

async function getJson<T>(path: string, timeoutMs = 4000): Promise<T> {
  const res = await apiFetch(path, { signal: AbortSignal.timeout(timeoutMs) });
  return (await res.json()) as T;
}

function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : "无法连接后端";
}

/* ---------- 项目列表（多项目切换 / 侧栏） ---------- */

/** 项目列表；失败返回空数组（侧栏显示「未连接」，页面自己会渲染 Offline）。 */
export async function loadProjects(): Promise<ApiProject[]> {
  try {
    const data = await getJson<ApiProject[]>("/api/projects");
    return data;
  } catch {
    return [];
  }
}

export async function loadRequirements(projectId: number): Promise<RequirementFeed> {
  try {
    const data = await getJson<ApiRequirementList>(`/api/projects/${projectId}/requirements`);
    const items = data.items.map(toRequirement);
    return { items, source: "api", error: null, counts: countRequirements(items) };
  } catch (err) {
    // 连不上时返回空，不用 mock 伪装；页面统一渲染 <Offline />
    return {
      items: [],
      source: "mock",
      error: messageOf(err),
      counts: { total: 0, confirmed: 0, rejected: 0, pending: 0, ambiguous: 0 },
    };
  }
}

export async function loadDocumentCount(projectId: number): Promise<number> {
  try {
    const data = await getJson<{ total: number }>(`/api/projects/${projectId}/documents`);
    return data.total;
  } catch {
    return 0;
  }
}

/* ---------- P4：质量扫描 ---------- */

export type QualityKind = "ambiguous" | "conflict" | "missing_acceptance";

export interface QualityIssue {
  issue_id: string;
  fingerprint: string;
  kind: QualityKind;
  severity: string;
  title: string;
  detail: string;
  req_ids: string[];
  words: string[];
  decision: "open" | "confirmed" | "ignored";
}

export interface QualityFeed {
  items: QualityIssue[];
  total: number;
  open: number;
  decided: number;
  byKind: Record<string, number>;
  source: DataSource;
  error: string | null;
}

interface ApiQualitySummary {
  items: QualityIssue[];
  total: number;
  open: number;
  decided: number;
  by_kind: Record<string, number>;
}

export async function loadQuality(projectId: number): Promise<QualityFeed> {
  try {
    const data = await getJson<ApiQualitySummary>(`/api/projects/${projectId}/quality/issues`);
    return {
      items: data.items,
      total: data.total,
      open: data.open ?? 0,
      decided: data.decided ?? 0,
      byKind: data.by_kind ?? {},
      source: "api",
      error: null,
    };
  } catch (err) {
    return {
      items: [],
      total: 0,
      open: 0,
      decided: 0,
      byKind: {},
      source: "mock",
      error: messageOf(err),
    };
  }
}

/* ---------- P5：测试用例 ---------- */

export type CaseType = "normal" | "abnormal" | "boundary";

export interface TestCaseItem {
  tc_id: number;
  req_id: string | null;
  title: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  test_type: CaseType;
  status: string;
}

export interface CaseFeed {
  items: TestCaseItem[];
  total: number;
  byStatus: Record<string, number>;
  byType: Record<string, number>;
  source: DataSource;
  error: string | null;
}

interface ApiCaseList {
  items: TestCaseItem[];
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
}

export async function loadCases(projectId: number): Promise<CaseFeed> {
  try {
    const data = await getJson<ApiCaseList>(`/api/projects/${projectId}/cases`);
    return {
      items: data.items,
      total: data.total,
      byStatus: data.by_status ?? {},
      byType: data.by_type ?? {},
      source: "api",
      error: null,
    };
  } catch (err) {
    return {
      items: [],
      total: 0,
      byStatus: {},
      byType: {},
      source: "mock",
      error: messageOf(err),
    };
  }
}

/* ---------- P6：追踪矩阵 ---------- */

export interface TraceSummary {
  confirmed: number;
  covered: number;
  coverage_pct: number;
  linked_any: number;
  cases: number;
  reviewed_cases: number;
  uncovered: number;
}

export interface TraceRequirement {
  req_id: string;
  title: string;
  status: string;
  case_ids: number[];
  reviewed: number;
  covered: boolean;
}

export interface TraceCase {
  tc_id: number;
  title: string;
  test_type: CaseType;
  status: string;
  req_id: string | null;
}

export interface TraceFeed {
  summary: TraceSummary;
  requirements: TraceRequirement[];
  cases: TraceCase[];
  source: DataSource;
  error: string | null;
}

interface ApiTrace {
  summary: TraceSummary;
  requirements: TraceRequirement[];
  cases: TraceCase[];
}

const EMPTY_SUMMARY: TraceSummary = {
  confirmed: 0,
  covered: 0,
  coverage_pct: 0,
  linked_any: 0,
  cases: 0,
  reviewed_cases: 0,
  uncovered: 0,
};

export async function loadTrace(projectId: number): Promise<TraceFeed> {
  try {
    const data = await getJson<ApiTrace>(`/api/projects/${projectId}/trace`);
    return { ...data, source: "api", error: null };
  } catch (err) {
    return {
      summary: EMPTY_SUMMARY,
      requirements: [],
      cases: [],
      source: "mock",
      error: messageOf(err),
    };
  }
}

/* ---------- P7：版本比对 ---------- */

export interface DiffCase {
  tc_id: number;
  title: string;
  req_id: string | null;
  status: string;
  test_type: string;
}

export interface DiffChange {
  change_id: string;
  kind: "changed" | "added" | "removed";
  base_para: number | null;
  target_para: number | null;
  base_text: string;
  target_text: string;
  removed_numbers: string[];
  added_numbers: string[];
  req_ids: string[];
  cases: DiffCase[];
}

export interface DiffSummary {
  added: number;
  removed: number;
  changed: number;
  affected_requirements: number;
  affected_cases: number;
}

export interface DiffData {
  base: { doc_id: number; filename: string; version: string };
  target: { doc_id: number; filename: string; version: string };
  summary: DiffSummary;
  changes: DiffChange[];
}

export interface DiffFeed {
  available: boolean;
  data: DiffData | null;
  message: string | null;
  source: DataSource;
}

export async function loadDiff(projectId: number): Promise<DiffFeed> {
  try {
    const data = await getJson<DiffData>(`/api/projects/${projectId}/document-diff`, 5000);
    return { available: true, data, message: null, source: "api" };
  } catch (err) {
    // 400 = 文档不足两个版本，属于正常提示而不是离线
    if (err instanceof ApiError && err.status === 400) {
      return { available: false, data: null, message: err.message, source: "api" };
    }
    return { available: false, data: null, message: messageOf(err), source: "mock" };
  }
}

/* ---------- P8：质量报告 ---------- */

export interface ReportCounts {
  requirements: number;
  confirmed: number;
  rejected: number;
  pending: number;
  issues: number;
  ambiguous: number;
  conflict: number;
  missing_acceptance: number;
  cases: number;
  case_generated: number;
  case_reviewed: number;
  case_rejected: number;
  covered_requirements: number;
  uncovered: number;
  coverage_pct: number;
}

export interface ReportData {
  project: { project_id: number; project_name: string; description: string | null };
  documents: { doc_id: number; filename: string; version: string; paragraphs: number }[];
  counts: ReportCounts;
  generated_at: string;
}

export interface ReportFeed {
  data: ReportData | null;
  source: DataSource;
  error: string | null;
}

export async function loadReport(projectId: number): Promise<ReportFeed> {
  try {
    const data = await getJson<ReportData>(`/api/projects/${projectId}/report`);
    return { data, source: "api", error: null };
  } catch (err) {
    return { data: null, source: "mock", error: messageOf(err) };
  }
}

/* ---------- 执行记录（生成 ≠ 执行 ≠ 通过） ---------- */

export interface ExecutionItem {
  exec_id: number;
  project_id: number;
  tc_id: number;
  result: "pass" | "fail" | "blocked" | string;
  actual_result: string | null;
  comments: string | null;
  tester: string | null;
  signature: string | null;
  environment: string | null;
  executed_at: string | null;
}

export interface ExecutionFeed {
  items: ExecutionItem[];
  total: number;
}

export async function loadExecutions(projectId: number): Promise<ExecutionFeed> {
  try {
    const data = await getJson<ExecutionFeed>(`/api/projects/${projectId}/executions`);
    return { items: data.items ?? [], total: data.total ?? 0 };
  } catch {
    return { items: [], total: 0 };
  }
}

/* ---------- 全局搜索 ---------- */

interface ApiSearch {
  query: string;
  requirements: ApiRequirement[];
  cases: TestCaseItem[];
  quality: QualityIssue[];
  total: number;
}

export interface SearchFeed {
  query: string;
  requirements: Requirement[];
  cases: TestCaseItem[];
  quality: QualityIssue[];
  total: number;
  source: DataSource;
  error: string | null;
}

export async function loadSearch(projectId: number, keyword: string): Promise<SearchFeed> {
  try {
    const data = await getJson<ApiSearch>(
      `/api/projects/${projectId}/search?q=${encodeURIComponent(keyword)}`,
      8000,
    );
    return {
      query: data.query,
      requirements: data.requirements.map(toRequirement),
      cases: data.cases,
      quality: data.quality,
      total: data.total,
      source: "api",
      error: null,
    };
  } catch (err) {
    return {
      query: keyword,
      requirements: [],
      cases: [],
      quality: [],
      total: 0,
      source: "mock",
      error: messageOf(err),
    };
  }
}

/* ---------- 文档工作台用的组合取数 ---------- */

export interface DocumentWorkspaceFeed {
  doc: ApiDocumentMeta | null;
  paragraphs: ApiParagraph[];
  requirements: Requirement[];
  requirementsError: string | null;
}

/** 文档工作台一次取齐：最新文档 + 段落 + 需求（需求失败不影响文档展示）。 */
export async function loadDocumentWorkspace(projectId: number): Promise<DocumentWorkspaceFeed> {
  const docs = await listDocuments(projectId);
  const doc = docs[0] ?? null;
  const paragraphs = doc ? await getParagraphs(doc.doc_id) : [];
  const feed = await loadRequirements(projectId);
  return { doc, paragraphs, requirements: feed.items, requirementsError: feed.error };
}
