"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_MAIN, NAV_STEPS } from "@/lib/nav";

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/");
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
            <path d="M4 7h16M4 12h11M4 17h14" />
          </svg>
        </div>
        <div>
          <div className="brand-name">RATGP</div>
          <div className="brand-sub">需求工程工作台</div>
        </div>
      </div>

      <div className="proj" title="P1 阶段固定为示例项目，P2 接入项目切换">
        <div className="av">选</div>
        <div className="nm">
          <b>校园选课系统</b>
          <span>V1.0 · 25 条需求</span>
        </div>
        <svg className="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>

      <nav className="nav">
        <div className="nav-label">项目</div>
        {NAV_MAIN.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item${isActive(pathname, item.href) ? " active" : ""}`}
          >
            <span className="ix">{item.num}</span>
            {item.label}
            {item.count ? <span className="cnt">{item.count}</span> : null}
          </Link>
        ))}

        <div className="nav-label">主线</div>
        {NAV_STEPS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item${isActive(pathname, item.href) ? " active" : ""}`}
          >
            <span className="ix">{item.num}</span>
            {item.label}
            {item.warn ? <span className="sd" style={{ background: "var(--warn)" }} /> : null}
            {item.count ? <span className="cnt">{item.count}</span> : null}
          </Link>
        ))}
      </nav>

      <div className="side-foot">
        <div className="avatar" style={{ width: 24, height: 24, fontSize: 10 }}>管</div>
        <div className="who">
          <b style={{ fontWeight: 600 }}>系统管理员</b>
          <br />
          <span>admin</span>
        </div>
        <svg style={{ marginLeft: "auto", color: "var(--text-3)" }} width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="5" cy="12" r="1.5" />
          <circle cx="12" cy="12" r="1.5" />
          <circle cx="19" cy="12" r="1.5" />
        </svg>
      </div>
    </aside>
  );
}
