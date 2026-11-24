"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import type { ApiProject } from "@/lib/api";
import { NAV_MAIN, NAV_STEPS, normalizePath } from "@/lib/nav";
import { Icon } from "./icon";

export interface SidebarCounts {
  documents: string;
  requirements: string;
  issues: string;
  cases: string;
  coverage: string;
  changes: string;
}

function isActive(pathname: string, href: string) {
  const path = normalizePath(pathname);
  return path === href || path.startsWith(href + "/");
}

export function Sidebar({
  counts,
  projects,
  currentProjectId,
  currentProjectName,
  onSelectProject,
  onCreateProject,
  onRenameProject,
  onDeleteProject,
}: {
  counts: SidebarCounts;
  projects: ApiProject[];
  currentProjectId: number;
  currentProjectName: string | null;
  onSelectProject: (projectId: number) => void;
  onCreateProject: () => void;
  onRenameProject: () => void;
  onDeleteProject: () => void;
}) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // 点菜单外面 / 按 Esc 关闭
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (event: MouseEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  const current = projects.find((project) => project.project_id === currentProjectId) ?? null;
  const projectName = current?.project_name ?? currentProjectName;
  const countOf = (key?: string) =>
    key ? (counts as unknown as Record<string, string>)[key] : undefined;

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

      <div className="proj-wrap" ref={wrapRef}>
        <button
          className="proj"
          type="button"
          title="切换 / 管理项目"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <div className="av">{(projectName ?? "选").slice(0, 1)}</div>
          <div className="nm">
            <b>{projectName ?? "未选择项目"}</b>
            <span>
              {counts.requirements} 条需求 · {counts.documents} 份文档
            </span>
          </div>
          <svg className="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>

        {menuOpen ? (
          <div className="proj-menu" role="menu">
            <div className="proj-menu-label">项目（{projects.length}）</div>
            {projects.length === 0 ? (
              <div className="proj-menu-empty">还没有项目，先新建一个</div>
            ) : null}
            {projects.map((project) => (
              <button
                key={project.project_id}
                type="button"
                role="menuitem"
                className={`proj-item${project.project_id === currentProjectId ? " on" : ""}`}
                onClick={() => {
                  setMenuOpen(false);
                  onSelectProject(project.project_id);
                }}
              >
                <span className="pn">{project.project_name}</span>
                <span className="pc">{project.req_count}</span>
              </button>
            ))}

            <div className="proj-menu-sep" />

            <button
              type="button"
              role="menuitem"
              className="proj-item action"
              onClick={() => {
                setMenuOpen(false);
                onCreateProject();
              }}
            >
              <Icon name="plus" size={13} />
              新建项目
            </button>
            <button
              type="button"
              role="menuitem"
              className="proj-item action"
              disabled={!current}
              onClick={() => {
                setMenuOpen(false);
                onRenameProject();
              }}
            >
              <Icon name="doc" size={13} />
              重命名 / 改描述
            </button>
            <button
              type="button"
              role="menuitem"
              className="proj-item action danger"
              disabled={!current}
              onClick={() => {
                setMenuOpen(false);
                onDeleteProject();
              }}
            >
              <Icon name="x" size={13} />
              删除当前项目
            </button>
          </div>
        ) : null}
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
          </Link>
        ))}

        <div className="nav-label">主线</div>
        {NAV_STEPS.map((item) => {
          const count = countOf(item.countKey);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item${isActive(pathname, item.href) ? " active" : ""}`}
            >
              <span className="ix">{item.num}</span>
              {item.label}
              {item.warn ? <span className="sd" style={{ background: "var(--warn)" }} /> : null}
              {count ? <span className="cnt">{count}</span> : null}
            </Link>
          );
        })}
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
