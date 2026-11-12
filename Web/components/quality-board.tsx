"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { QualityFeed, QualityIssue } from "@/lib/server";
import { Icon } from "./icon";

type Filter = "all" | QualityIssue["kind"];

const KIND_META: Record<QualityIssue["kind"], { label: string; chip: string }> = {
  ambiguous: { label: "模糊表达", chip: "warn" },
  conflict: { label: "需求冲突", chip: "danger" },
  missing_acceptance: { label: "缺验收", chip: "" },
};

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "ambiguous", label: "模糊" },
  { id: "conflict", label: "冲突" },
  { id: "missing_acceptance", label: "缺验收" },
];

export function QualityBoard({ feed }: { feed: QualityFeed }) {
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(
    () =>
      ({
        all: feed.total,
        ambiguous: feed.byKind.ambiguous ?? 0,
        conflict: feed.byKind.conflict ?? 0,
        missing_acceptance: feed.byKind.missing_acceptance ?? 0,
      }) as Record<Filter, number>,
    [feed],
  );

  const rows = useMemo(
    () => (filter === "all" ? feed.items : feed.items.filter((i) => i.kind === filter)),
    [feed.items, filter],
  );

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 04 · 质量</div>
          <h1 className="page-title">
            质量分析
            {feed.source === "mock" ? (
              <span className="chip warn" title={feed.error ?? "后端未连接"}>
                示例数据
              </span>
            ) : null}
          </h1>
          <div className="page-sub">
            规则引擎给出可复现的问题，结论由人确认。同一份数据每次扫描结果一致。
          </div>
        </div>
        <div className="head-actions">
          <a className="btn" href="/quality">
            <Icon name="filter" size={13} />
            重新扫描
          </a>
        </div>
      </div>

      <div className="strip">
        <div className="metric">
          <div className="k">问题总数</div>
          <div className="v">
            {feed.total}
            <small>条</small>
          </div>
          <div className="d">确定性规则，可复算</div>
        </div>
        <div className="metric">
          <div className="k">模糊表达</div>
          <div className="v">
            {counts.ambiguous}
            <small>条</small>
          </div>
          <div className="d">命中词表，建议补量化指标</div>
        </div>
        <div className="metric">
          <div className="k">需求冲突</div>
          <div className="v">
            {counts.conflict}
            <small>条</small>
          </div>
          <div className="d">数值口径 + 相反表述</div>
        </div>
        <div className="metric">
          <div className="k">缺验收条件</div>
          <div className="v">
            {counts.missing_acceptance}
            <small>条</small>
          </div>
          <div className="d">无法判断是否实现</div>
        </div>
      </div>

      <div className="toolbar" style={{ marginTop: 14 }}>
        <div className="seg">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={filter === f.id ? "on" : ""}
              onClick={() => setFilter(f.id)}
            >
              {f.label} <span className="n">{counts[f.id]}</span>
            </button>
          ))}
        </div>
        <div className="sp" />
        <span className="st idle">冲突检测目前覆盖可量化口径与相反表述，语义冲突留人工</span>
      </div>

      {feed.source === "mock" ? (
        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name="alert" size={20} />
            </div>
            <h3>后端没有连上</h3>
            <p>启动 FastAPI（8000）后刷新本页，质量扫描会基于真实需求表计算。</p>
            <div className="row">
              <a className="btn" href="/quality">
                重试
              </a>
            </div>
          </div>
        </div>
      ) : rows.length === 0 ? (
        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name="shield" size={20} />
            </div>
            <h3>{filter === "all" ? "没有发现问题" : "这一类没有问题"}</h3>
            <p>
              {filter === "all"
                ? "当前需求都通过了规则检查。注意这不等于需求一定正确，语义层面的判断仍需人工。"
                : "换一个筛选条件看看。"}
            </p>
            <div className="row">
              <Link className="btn" href="/requirements">
                去看需求库
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="issue-list">
            {rows.map((issue) => {
              const meta = KIND_META[issue.kind];
              return (
                <div className="issue" key={issue.issue_id}>
                  <span
                    className="dot"
                    style={{ background: issue.severity === "danger" ? "var(--danger)" : "var(--warn)" }}
                  />
                  <div className="iss-main">
                    <div className="iss-title">
                      <span className={`chip ${meta.chip}`}>{meta.label}</span>
                      {issue.title}
                    </div>
                    <div className="iss-sub">{issue.detail}</div>
                  </div>
                  <div className="iss-ids">{issue.req_ids.join(" · ")}</div>
                  {issue.req_ids.length ? (
                    <Link className="btn sm" href={`/requirements?open=${issue.req_ids[0]}`}>
                      查看需求
                    </Link>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
