"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { decideQualityIssue } from "@/lib/api";
import type { QualityFeed, QualityIssue } from "@/lib/server";
import { Icon } from "./icon";

type KindFilter = "all" | QualityIssue["kind"];
type DecisionFilter = "all" | "open" | "confirmed" | "ignored";

const KIND_META: Record<QualityIssue["kind"], { label: string; chip: string }> = {
  ambiguous: { label: "模糊表达", chip: "warn" },
  conflict: { label: "需求冲突", chip: "danger" },
  missing_acceptance: { label: "缺验收", chip: "" },
};

const KIND_FILTERS: { id: KindFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "ambiguous", label: "模糊" },
  { id: "conflict", label: "冲突" },
  { id: "missing_acceptance", label: "缺验收" },
];

const DECISION_META: Record<string, { label: string; chip: string }> = {
  open: { label: "待处理", chip: "idle" },
  confirmed: { label: "已确认", chip: "danger" },
  ignored: { label: "已忽略", chip: "" },
};

const DECISION_FILTERS: { id: DecisionFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "open", label: "待处理" },
  { id: "confirmed", label: "已确认" },
  { id: "ignored", label: "已忽略" },
];

export function QualityBoard({ feed }: { feed: QualityFeed }) {
  const router = useRouter();
  const [kind, setKind] = useState<KindFilter>("all");
  const [decision, setDecision] = useState<DecisionFilter>("all");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const kindCounts = useMemo(
    () =>
      ({
        all: feed.total,
        ambiguous: feed.byKind.ambiguous ?? 0,
        conflict: feed.byKind.conflict ?? 0,
        missing_acceptance: feed.byKind.missing_acceptance ?? 0,
      }) as Record<KindFilter, number>,
    [feed],
  );

  const decisionCounts = useMemo(
    () =>
      ({
        all: feed.total,
        open: feed.items.filter((i) => i.decision === "open").length,
        confirmed: feed.items.filter((i) => i.decision === "confirmed").length,
        ignored: feed.items.filter((i) => i.decision === "ignored").length,
      }) as Record<DecisionFilter, number>,
    [feed],
  );

  const rows = useMemo(
    () =>
      feed.items.filter(
        (issue) =>
          (kind === "all" || issue.kind === kind) &&
          (decision === "all" || issue.decision === decision),
      ),
    [feed.items, kind, decision],
  );

  async function decide(issue: QualityIssue, next: "confirmed" | "ignored" | "open") {
    setBusy(issue.fingerprint);
    setError(null);
    try {
      await decideQualityIssue(1, issue.fingerprint, next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(null);
    }
  }

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
            规则引擎给出可复现的问题，逐条「确认 / 忽略」留下裁决；同一份数据每次扫描结果一致。
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
          <div className="k">待处理</div>
          <div className="v">
            {decisionCounts.open}
            <small>条</small>
          </div>
          <div className="d">还需要人工裁决</div>
        </div>
        <div className="metric">
          <div className="k">已确认</div>
          <div className="v">
            {decisionCounts.confirmed}
            <small>条</small>
          </div>
          <div className="d">问题成立，需要改需求</div>
        </div>
        <div className="metric">
          <div className="k">已忽略</div>
          <div className="v">
            {decisionCounts.ignored}
            <small>条</small>
          </div>
          <div className="d">误报或有意为之</div>
        </div>
      </div>

      <div className="toolbar" style={{ marginTop: 14 }}>
        <div className="seg">
          {KIND_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={kind === f.id ? "on" : ""}
              onClick={() => setKind(f.id)}
            >
              {f.label} <span className="n">{kindCounts[f.id]}</span>
            </button>
          ))}
        </div>
        <div className="sp" />
        <div className="seg">
          {DECISION_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={decision === f.id ? "on" : ""}
              onClick={() => setDecision(f.id)}
            >
              {f.label} <span className="n">{decisionCounts[f.id]}</span>
            </button>
          ))}
        </div>
      </div>

      {error ? <div className="extract-status error">{error}</div> : null}

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
            <h3>{feed.total === 0 ? "没有发现问题" : "这一组没有条目"}</h3>
            <p>
              {feed.total === 0
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
              const dm = DECISION_META[issue.decision] ?? DECISION_META.open;
              const working = busy === issue.fingerprint;
              return (
                <div className="issue" key={issue.fingerprint}>
                  <span
                    className="dot"
                    style={{
                      background:
                        issue.severity === "danger" ? "var(--danger)" : "var(--warn)",
                    }}
                  />
                  <div className="iss-main">
                    <div className="iss-title">
                      <span className={`chip ${meta.chip}`}>{meta.label}</span>
                      {issue.title}
                      <span className={`chip ${dm.chip}`}>{dm.label}</span>
                    </div>
                    <div className="iss-sub">{issue.detail}</div>
                  </div>
                  <div className="iss-ids">{issue.req_ids.join(" · ")}</div>
                  {issue.req_ids.length ? (
                    <Link className="btn sm" href={`/requirements?open=${issue.req_ids[0]}`}>
                      查看需求
                    </Link>
                  ) : null}
                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    <button
                      className="btn sm"
                      type="button"
                      disabled={working || issue.decision === "confirmed"}
                      onClick={() => decide(issue, "confirmed")}
                    >
                      确认
                    </button>
                    <button
                      className="btn sm ghost"
                      type="button"
                      disabled={working || issue.decision === "ignored"}
                      onClick={() => decide(issue, "ignored")}
                    >
                      忽略
                    </button>
                    {issue.decision !== "open" ? (
                      <button
                        className="btn sm ghost"
                        type="button"
                        disabled={working}
                        onClick={() => decide(issue, "open")}
                      >
                        撤销
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
