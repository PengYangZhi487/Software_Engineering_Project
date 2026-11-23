"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { TraceFeed, TraceRequirement } from "@/lib/server";
import { Icon } from "./icon";

const TYPE_LABEL: Record<string, string> = { normal: "正常", abnormal: "异常", boundary: "边界" };

const STATUS_META: Record<string, { label: string; cls: string }> = {
  已确认: { label: "已确认", cls: "ok" },
  未审核: { label: "未审核", cls: "idle" },
  已驳回: { label: "已驳回", cls: "danger" },
};

type ReqCaseCounts = {
  reviewed: number;
  generated: number;
  executed: number;
  rejected: number;
};

export function TraceBoard({ feed }: { feed: TraceFeed }) {
  const [onlyUncovered, setOnlyUncovered] = useState(false);
  const [mode, setMode] = useState<"summary" | "matrix">("summary");

  const { summary, cases, requirements } = feed;
  const ring = 2 * Math.PI * 30;
  const offset = ring * (1 - summary.coverage_pct / 100);

  const rows = useMemo(
    () =>
      onlyUncovered
        ? requirements.filter((r) => r.status === "已确认" && !r.covered)
        : requirements,
    [onlyUncovered, requirements],
  );

  const uncovered = useMemo(
    () => requirements.filter((r) => r.status === "已确认" && !r.covered),
    [requirements],
  );

  const perReq = useMemo(() => {
    const map = new Map<string, ReqCaseCounts>();
    for (const c of cases) {
      if (!c.req_id) continue;
      const item = map.get(c.req_id) ?? {
        reviewed: 0,
        generated: 0,
        executed: 0,
        rejected: 0,
      };
      if (c.status === "已审核") item.reviewed += 1;
      else if (c.status === "已生成") item.generated += 1;
      else if (c.status === "已执行") item.executed += 1;
      else if (c.status === "已驳回") item.rejected += 1;
      map.set(c.req_id, item);
    }
    return map;
  }, [cases]);

  const mock = feed.source === "mock";

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 06 · 追踪</div>
          <h1 className="page-title">
            追踪矩阵
            {mock ? (
              <span className="chip warn" title={feed.error ?? "后端未连接"}>
                示例数据
              </span>
            ) : null}
          </h1>
          <div className="page-sub">
            需求 × 测试用例。覆盖率 = 至少关联一条「已审核」用例的已确认需求 / 已确认需求总数。
          </div>
        </div>
        <div className="head-actions">
          <div className="seg">
            <button
              type="button"
              className={mode === "summary" ? "on" : ""}
              onClick={() => setMode("summary")}
            >
              汇总
            </button>
            <button
              type="button"
              className={mode === "matrix" ? "on" : ""}
              onClick={() => setMode("matrix")}
            >
              矩阵
            </button>
          </div>
          <div className="seg">
            <button type="button" className={!onlyUncovered ? "on" : ""} onClick={() => setOnlyUncovered(false)}>
              全部
            </button>
            <button type="button" className={onlyUncovered ? "on" : ""} onClick={() => setOnlyUncovered(true)}>
              仅未覆盖 <span className="n">{summary.uncovered}</span>
            </button>
          </div>
          <Link className="btn" href="/cases">
            <Icon name="flask" size={13} />
            去生成用例
          </Link>
        </div>
      </div>

      {mock ? (
        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name="alert" size={20} />
            </div>
            <h3>后端没有连上</h3>
            <p>启动 FastAPI（8000）后刷新，矩阵会用真实的需求与用例关联计算。</p>
          </div>
        </div>
      ) : (
        <>
          <div className="mx-head">
            <div className="ring">
              <svg width="72" height="72" viewBox="0 0 72 72">
                <circle cx="36" cy="36" r="30" fill="none" stroke="var(--line)" strokeWidth="5" />
                <circle
                  cx="36"
                  cy="36"
                  r="30"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray={ring}
                  strokeDashoffset={offset}
                  transform="rotate(-90 36 36)"
                />
              </svg>
              <div className="lb">
                <div>
                  <b>{summary.coverage_pct}%</b>
                  <span>覆盖率</span>
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.85 }}>
                <b style={{ color: "var(--text)" }}>
                  {summary.covered} / {summary.confirmed}
                </b>{" "}
                条已确认需求至少关联 1 条已审核用例
                <br />
                <span style={{ color: "var(--text-3)", fontSize: 11.5 }}>
                  用例 {summary.cases} 条，其中已审核 {summary.reviewed_cases} 条；仅关联未审核用例不计入分子
                </span>
              </div>
            </div>

            <div style={{ marginLeft: "auto" }} className="legend">
              <span>
                <i className="mk on" />
                已关联
              </span>
              <span>
                <i className="mk off" />
                未覆盖
              </span>
              <span style={{ color: "var(--warn)" }}>
                <i className="dot" style={{ background: "var(--warn)" }} />
                已生成未审核
              </span>
            </div>
          </div>

          {cases.length === 0 ? (
            <div className="card">
              <div className="empty">
                <div className="ic">
                  <Icon name="grid" size={20} />
                </div>
                <h3>还没有测试用例</h3>
                <p>矩阵的行是需求、列是用例。先去用例工作台按已确认需求生成一批。</p>
                <div className="row">
                  <Link className="btn primary" href="/cases">
                    去生成用例
                  </Link>
                </div>
              </div>
            </div>
          ) : mode === "summary" ? (
            <SummaryTable rows={rows} perReq={perReq} />
          ) : (
            <div className="mx-split">
              <div className="mx">
                <table>
                  <thead>
                    <tr>
                      <th className="rowh" style={{ zIndex: 4 }}>
                        需求 <span style={{ color: "var(--text-3)", fontWeight: 400 }}>{rows.length}</span>
                      </th>
                      {cases.map((c) => (
                        <th key={c.tc_id} className="ct" title={c.title}>
                          {String(c.tc_id).padStart(3, "0")}
                          <span className="ty">{TYPE_LABEL[c.test_type] ?? c.test_type}</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.req_id} className={r.covered ? "" : "uncovered"}>
                        <th className="rowh">
                          <span className="rid">{r.req_id}</span>
                          <span className="rt">{r.title}</span>
                        </th>
                        {cases.map((c) => {
                          const linked = r.case_ids.includes(c.tc_id);
                          const reviewed = linked && c.status === "已审核";
                          return (
                            <td className="c" key={c.tc_id} title={linked ? `${c.title}（${c.status}）` : "未关联"}>
                              {reviewed ? (
                                <i className="mk on" />
                              ) : linked ? (
                                <i className="mk pending" />
                              ) : (
                                <i className="mk off" />
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={cases.length + 1} style={{ padding: 28, textAlign: "center", color: "var(--text-3)" }}>
                          没有符合条件的需求
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="card">
                <div className="card-h">
                  <span className="t">未覆盖需求</span>
                  <span className="m">{uncovered.length} 条</span>
                </div>
                <div className="card-b" style={{ paddingTop: 10 }}>
                  {uncovered.length === 0 ? (
                    <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.8 }}>
                      所有已确认需求都有关联的已审核用例。
                    </div>
                  ) : (
                    uncovered.map((r) => (
                      <Link
                        key={r.req_id}
                        href={`/requirements?open=${r.req_id}`}
                        className="todo"
                        style={{ padding: "9px 0", textDecoration: "none", gap: 10 }}
                      >
                        <div
                          style={{
                            width: 14,
                            display: "flex",
                            justifyContent: "center",
                            flex: "none",
                          }}
                        >
                          <span
                            className="dot"
                            style={{ background: r.case_ids.length ? "var(--warn)" : "var(--line-strong)" }}
                          />
                        </div>
                        <div style={{ minWidth: 0 }}>
                          <div className="tt" style={{ fontSize: 12 }}>
                            {r.title}
                          </div>
                          <div className="ts">
                            {r.req_id} · {r.case_ids.length ? "用例待审核" : "未生成用例"}
                          </div>
                        </div>
                        <Icon name="right" size={13} style={{ marginLeft: "auto", color: "var(--text-3)" }} />
                      </Link>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function SummaryTable({
  rows,
  perReq,
}: {
  rows: TraceRequirement[];
  perReq: Map<string, ReqCaseCounts>;
}) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <table className="trace-summary">
        <thead>
          <tr>
            <th>需求</th>
            <th style={{ width: 90 }}>状态</th>
            <th style={{ width: 76, textAlign: "right" }}>已审核</th>
            <th style={{ width: 76, textAlign: "right" }}>已生成</th>
            <th style={{ width: 76, textAlign: "right" }}>已执行</th>
            <th style={{ width: 76, textAlign: "right" }}>已驳回</th>
            <th style={{ width: 110 }}>覆盖</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const c = perReq.get(r.req_id) ?? {
              reviewed: 0,
              generated: 0,
              executed: 0,
              rejected: 0,
            };
            const meta = STATUS_META[r.status] ?? { label: r.status, cls: "" };
            return (
              <tr key={r.req_id} className={r.covered ? "" : "uncovered"}>
                <td>
                  <Link href={`/requirements?open=${r.req_id}`} style={{ textDecoration: "none" }}>
                    <span className="rid">{r.req_id}</span>
                    <span className="rt">{r.title}</span>
                  </Link>
                </td>
                <td>
                  <span className={`st ${meta.cls}`}>
                    <span className="dot" />
                    {meta.label}
                  </span>
                </td>
                <td className="num">{c.reviewed}</td>
                <td className="num">{c.generated}</td>
                <td className="num">{c.executed}</td>
                <td className="num">{c.rejected}</td>
                <td>
                  {r.covered ? (
                    <span className="chip ok">已覆盖</span>
                  ) : r.case_ids.length ? (
                    <span className="chip warn">待审核</span>
                  ) : (
                    <span className="chip">未生成</span>
                  )}
                </td>
              </tr>
            );
          })}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={7} style={{ textAlign: "center", padding: 28, color: "var(--text-3)" }}>
                没有符合条件的需求
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
