import { stats } from "./stats";

export interface NavItem {
  href: string;
  num: string;
  label: string;
  count?: string;
  warn?: boolean;
}

export const NAV_MAIN: NavItem[] = [
  { href: "/overview", num: "01", label: "总览" },
];

export const NAV_STEPS: NavItem[] = [
  { href: "/document", num: "02", label: "文档", count: "1" },
  { href: "/requirements", num: "03", label: "需求", count: String(stats.total) },
  { href: "/quality", num: "04", label: "质量", count: String(stats.issues), warn: true },
  { href: "/cases", num: "05", label: "用例", count: String(stats.cases) },
  { href: "/trace", num: "06", label: "追踪", count: `${stats.coveragePct}%` },
  { href: "/changes", num: "07", label: "变更" },
  { href: "/report", num: "08", label: "报告" },
];

export const NAV_ALL = [...NAV_MAIN, ...NAV_STEPS];

export const TITLES: Record<string, string> = {
  "/overview": "总览",
  "/document": "文档",
  "/requirements": "需求",
  "/quality": "质量",
  "/cases": "用例",
  "/trace": "追踪",
  "/changes": "变更",
  "/report": "报告",
};

export function titleOf(pathname: string): string {
  return TITLES[pathname] ?? "总览";
}
