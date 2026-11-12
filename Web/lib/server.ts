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
