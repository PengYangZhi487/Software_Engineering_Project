export interface NavItem {
  href: string;
  num: string;
  label: string;
  /** 对应 Sidebar 传入的 counts 键名 */
  countKey?: string;
  warn?: boolean;
}

export const NAV_MAIN: NavItem[] = [{ href: "/overview", num: "01", label: "总览" }];

export const NAV_STEPS: NavItem[] = [
  { href: "/document", num: "02", label: "文档", countKey: "documents" },
  { href: "/requirements", num: "03", label: "需求", countKey: "requirements" },
  { href: "/quality", num: "04", label: "质量", countKey: "issues", warn: true },
  { href: "/cases", num: "05", label: "用例", countKey: "cases" },
  { href: "/trace", num: "06", label: "追踪", countKey: "coverage" },
  { href: "/changes", num: "07", label: "变更" },
  { href: "/report", num: "08", label: "报告" },
];

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
