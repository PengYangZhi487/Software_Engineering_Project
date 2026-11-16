/**
 * 服务端数据入口：优先读 FastAPI，连不上时退回本地 mock（页面不至于白屏）。
 * 只在 Server Component 里调用。
 */
import { API_BASE } from "./api";
import { requirements as mockRequirements } from "./data";
import type { DataSource, Requirement, Risk } from "./types";

interface ApiRequirement {
  req_id: string;
  project_id: number;
  title: string;
  description: string;
  req_type: string;
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
    title: row.title,
    desc: row.description,
    type: row.req_type === "non_functional" ? "non_functional" : "functional",
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
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) throw new Error(`API ${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function loadRequirements(projectId = 1): Promise<RequirementFeed> {
  try {
    const data = await getJson<ApiRequirementList>(`/api/projects/${projectId}/requirements`);
    const items = data.items.map(toRequirement);
    return { items, source: "api", error: null, counts: countRequirements(items) };
  } catch (err) {
    return {
      items: mockRequirements,
      source: "mock",
      error: err instanceof Error ? err.message : "无法连接后端",
      counts: countRequirements(mockRequirements),
    };
  }
}

export async function loadDocumentCount(projectId = 1): Promise<number> {
  try {
    const data = await getJson<{ total: number }>(`/api/projects/${projectId}/documents`);
    return data.total;
  } catch {
    return 1; // mock 状态：P0 里的示例文档
  }
}

/* ---------- P4：质量扫描 ---------- */

export type QualityKind = "ambiguous" | "conflict" | "missing_acceptance";

export interface QualityIssue {
  issue_id: string;
  kind: QualityKind;
  severity: string;
  title: string;
  detail: string;
  req_ids: string[];
  words: string[];
}

export interface QualityFeed {
  items: QualityIssue[];
  total: number;
  byKind: Record<string, number>;
  source: DataSource;
  error: string | null;
}

interface ApiQualitySummary {
  items: QualityIssue[];
  total: number;
  by_kind: Record<string, number>;
}

export async function loadQuality(projectId = 1): Promise<QualityFeed> {
  try {
    const data = await getJson<ApiQualitySummary>(`/api/projects/${projectId}/quality/issues`);
    return {
      items: data.items,
      total: data.total,
      byKind: data.by_kind ?? {},
      source: "api",
      error: null,
    };
  } catch (err) {
    return {
      items: [],
      total: 0,
      byKind: {},
      source: "mock",
      error: err instanceof Error ? err.message : "无法连接后端",
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

export async function loadCases(projectId = 1): Promise<CaseFeed> {
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
      error: err instanceof Error ? err.message : "无法连接后端",
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

export async function loadTrace(projectId = 1): Promise<TraceFeed> {
  try {
    const data = await getJson<ApiTrace>(`/api/projects/${projectId}/trace`);
    return { ...data, source: "api", error: null };
  } catch (err) {
    return {
      summary: EMPTY_SUMMARY,
      requirements: [],
      cases: [],
      source: "mock",
      error: err instanceof Error ? err.message : "无法连接后端",
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

export async function loadDiff(projectId = 1): Promise<DiffFeed> {  try {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/document-diff`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (res.status === 400) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      return {
        available: false,
        data: null,
        message: body?.detail ?? "至少需要两个版本的文档",
        source: "api",
      };
    }
    if (!res.ok) throw new Error(`API ${res.status} ${res.statusText}`);

    const data = (await res.json()) as DiffData;
    return { available: true, data, message: null, source: "api" };
  } catch (err) {
    return {
      available: false,
      data: null,
      message: err instanceof Error ? err.message : "无法连接后端",
      source: "mock",
    };
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

export async function loadReport(projectId = 1): Promise<ReportFeed> {
  try {
    const data = await getJson<ReportData>(`/api/projects/${projectId}/report`);
    return { data, source: "api", error: null };
  } catch (err) {
    return {
      data: null,
      source: "mock",
      error: err instanceof Error ? err.message : "无法连接后端",
    };
  }
}
