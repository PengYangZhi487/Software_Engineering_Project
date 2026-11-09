import type { CSSProperties, ReactNode } from "react";

export type IconName =
  | "search" | "upload" | "flask" | "more" | "down" | "plus" | "x" | "alert"
  | "check" | "chev" | "right" | "sun" | "moon" | "drop" | "doc" | "quote"
  | "filter" | "shield" | "diff" | "chart" | "flow" | "grid";

const PATHS: Record<IconName, ReactNode> = {
  search: <><circle cx="11" cy="11" r="7" /><path d="M16.5 16.5L21 21" /></>,
  upload: <><path d="M12 16V4M7 9l5-5 5 5M4 15v4a1 1 0 001 1h14a1 1 0 001-1v-4" /></>,
  flask: <><path d="M9 3h6M10 3v6L5 18a2 2 0 001.8 3h10.4A2 2 0 0019 18l-5-9V3" /><path d="M7.5 14h9" /></>,
  more: <g fill="currentColor" stroke="none"><circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" /></g>,
  down: <><path d="M12 4v12M7 11l5 5 5-5M5 20h14" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  x: <><path d="M6 6l12 12M18 6L6 18" /></>,
  alert: <><path d="M12 3l9 16H3L12 3z" /><path d="M12 10v4M12 17v.5" /></>,
  check: <><path d="M4 12.5l5 5L20 6.5" /></>,
  chev: <><path d="M6 9l6 6 6-6" /></>,
  right: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /></>,
  moon: <><path d="M20 14.2A8.4 8.4 0 019.8 4 8.5 8.5 0 1020 14.2z" /></>,
  drop: <><path d="M12 3.2s6.2 6.4 6.2 10.4a6.2 6.2 0 11-12.4 0C5.8 9.6 12 3.2 12 3.2z" /></>,
  doc: <><path d="M6 2.5h7l5 5v14H6z" /><path d="M13 2.5v5h5" /></>,
  quote: <><path d="M4 5h16M4 10h10M4 15h16M4 20h10" /></>,
  filter: <><path d="M3 5h18M7 12h10M10 19h4" /></>,
  shield: <><path d="M12 2.8l7.5 3v6c0 4.5-3.1 8-7.5 9.4C7.6 19.8 4.5 16.3 4.5 11.8v-6z" /><path d="M9 12l2 2 4-4" /></>,
  diff: <><path d="M8 3v14M8 17l-3-3M8 17l3-3" /><path d="M16 21V7M16 7l-3 3M16 7l3 3" /></>,
  chart: <><path d="M4 20V9M10 20V4M16 20v-7M22 20H2" /></>,
  flow: <><rect x="3" y="3.5" width="6" height="5" rx="1.4" /><rect x="15" y="9.5" width="6" height="5" rx="1.4" /><rect x="3" y="15.5" width="6" height="5" rx="1.4" /><path d="M9 6h3a3 3 0 013 3v.5M9 18h3a3 3 0 003-3v-.5" /></>,
  grid: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.6" /><rect x="13.5" y="3.5" width="7" height="7" rx="1.6" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.6" /><rect x="13.5" y="13.5" width="7" height="7" rx="1.6" /></>,
};

export function Icon({
  name,
  size = 14,
  className,
  style,
}: {
  name: IconName;
  size?: number;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
