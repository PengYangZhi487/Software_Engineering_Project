"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch, batchUpdateCases, exportCasesUrl, formatApiTime } from "@/lib/api";
import type { CaseFeed, ExecutionItem, TestCaseItem } from "@/lib/server";
import type { Requirement } from "@/lib/types";
import { CaseForm } from "./case-form";
import { ExecutionForm } from "./execution-form";
import { ImportDialog } from "./import-dialog";
import { Icon } from "./icon";

type StatusFilter = "all" | "已生成" | "已审核" | "已驳回" | "已执行";

const TYPE_LABEL: Record<string, string> = { normal: "正常", abnormal: "异常", boundary: "边界" };
const TYPE_CHIP: Record<string, string> = { normal: "ok", abnormal: "warn", boundary: "accent" };
const STATUS_CHIP: Record<string, string> = {
  已生成: "idle",
  已审核: "ok",
  已驳回: "danger",
  已执行: "accent",
};
const RESULT_LABEL: Record<string, string> = { pass: "通过", fail: "失败", blocked: "阻塞" };
const RESULT_CHIP: Record<string, string> = { pass: "ok", fail: "danger", blocked: "warn" };

const FILTERS: { id: StatusFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "已生成", label: "已生成" },
  { id: "已审核", label: "已审核" },
  { id: "已驳回", label: "已驳回" },
  { id: "已执行", label: "已执行" },
];

export function CaseBoard({
  feed,
  requirements,
  executions,
}: {
  feed: CaseFeed;
  requirements: Requirement[];
  executions: ExecutionItem[];
}) {
  const router = useRouter();
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [genOpen, setGenOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [generating, setGenerating] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<TestCaseItem | null>(null);
  const [selectedCases, setSelectedCases] = useState<Set<number>>(new Set());
  const [batchBusy, setBatchBusy] = useState(false);
  const [execOpen, setExecOpen] = useState(false);
  const [execTarget, setExecTarget] = useState<TestCaseItem | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const confirmed = useMemo(() => requirements.filter((r) => r.status === "confirmed"), [requirements]);

  const counts = useMemo(
    () =>
      ({
        all: feed.total,
        已生成: feed.byStatus["已生成"] ?? 0,
        已审核: feed.byStatus["已审核"] ?? 0,
        已驳回: feed.byStatus["已驳回"] ?? 0,
        已执行: feed.byStatus["已执行"] ?? 0,
      }) as Record<StatusFilter, number>,
    [feed],
  );

  const rows = useMemo(
    () => (filter === "all" ? feed.items : feed.items.filter((c) => c.status === filter)),
    [feed.items, filter],
  );

  // 执行记录按 tc_id 取最新一条（接口按 exec_id 升序返回）
  const latestByTc = useMemo(() => {
    const map = new Map<number, ExecutionItem>();
    for (const item of executions) map.set(item.tc_id, item);
    return map;
  }, [executions]);

  const allChecked = rows.length > 0 && rows.every((c) => selectedCases.has(c.tc_id));

  useEffect(() => {
    if (!generating) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    setElapsed(0);
    timer.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [generating]);

  function toggleReq(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleCase(tcId: number) {
    setSelectedCases((prev) => {
      const next = new Set(prev);
      if (next.has(tcId)) next.delete(tcId);
      else next.add(tcId);
      return next;
    });
  }

  function toggleAllCases() {
    setSelectedCases(allChecked ? new Set() : new Set(rows.map((c) => c.tc_id)));
  }

  async function generate() {
    const ids = selected.size ? [...selected] : confirmed.map((r) => r.id);
    if (!ids.length) {
      setMessage({ kind: "error", text: "没有已确认的需求，先去需求库确认几条" });
      return;
    }
    setGenerating(true);
    setMessage(null);
    try {
      const res = await apiFetch("/api/projects/1/cases/generate", {
        method: "POST",
        body: JSON.stringify({ req_ids: ids, replace: true }),
      });
      const data = (await res.json()) as { created?: number; skipped?: number };
      setGenOpen(false);
      setSelected(new Set());
      setMessage({
        kind: "ok",
        text: `已生成 ${data.created ?? 0} 条用例${data.skipped ? `，${data.skipped} 条写入失败` : ""}`,
      });
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        window.dispatchEvent(new Event("ratgp-open-key-dialog"));
      }
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "生成失败" });
    } finally {
      setGenerating(false);
    }
  }

  async function review(c: TestCaseItem, status: string) {
    setBusyId(c.tc_id);
    try {
      await apiFetch(`/api/projects/1/cases/${c.tc_id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      router.refresh();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "保存失败" });
    } finally {
      setBusyId(null);
    }
  }

  async function batchReview(status: string) {
    if (!selectedCases.size) return;
    setBatchBusy(true);
    try {
      const updated = await batchUpdateCases(1, [...selectedCases], status);
      setMessage({ kind: "ok", text: `已批量更新 ${updated} 条用例` });
      setSelectedCases(new Set());
      router.refresh();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "批量更新失败" });
    } finally {
      setBatchBusy(false);
    }
  }

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 05 · 用例</div>
          <h1 className="page-title">
            测试用例
            {feed.source === "mock" ? (
              <span className="chip warn" title={feed.error ?? "后端未连接"}>
                示例数据
              </span>
            ) : null}
          </h1>
          <div className="page-sub">
            按已确认需求批量生成正常 / 异常 / 边界候选用例，逐条审核、记录执行。生成 ≠ 通过。
          </div>
        </div>
        <div className="head-actions">
          <button
            className="btn"
            type="button"
            disabled={feed.source !== "api"}
            onClick={() => setImportOpen(true)}
          >
            <Icon name="upload" />导入
          </button>
          <a className="btn" href={exportCasesUrl(1)} download>
            <Icon name="down" />导出
          </a>
          <button
            className="btn primary"
            type="button"
            disabled={generating || feed.source !== "api"}
            onClick={() => {
              setGenOpen((v) => !v);
              setMessage(null);
            }}
          >
            <Icon name="flask" />
            {generating ? `生成中 ${elapsed}s` : "生成用例"}
          </button>
        </div>
      </div>

      <div className="strip">
        <div className="metric">
          <div className="k">用例总数</div>
          <div className="v">
            {feed.total}
            <small>条</small>
          </div>
          <div className="d">来自已确认需求</div>
        </div>
        <div className="metric">
          <div className="k">已生成</div>
          <div className="v">
            {counts["已生成"]}
            <small>条</small>
          </div>
          <div className="d">待人工审核</div>
        </div>
        <div className="metric">
          <div className="k">已审核</div>
          <div className="v">
            {counts["已审核"]}
            <small>条</small>
          </div>
          <div className="d">可用于覆盖率统计</div>
        </div>
        <div className="metric">
          <div className="k">执行记录</div>
          <div className="v">
            {executions.length}
            <small>次</small>
          </div>
          <div className="d">实际执行结果（含 comments / 签名）</div>
        </div>
      </div>

      {genOpen ? (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="card-h">
            <span className="t">选择要生成用例的需求</span>
            <span className="m">
              已选 {selected.size || confirmed.length} / 共 {confirmed.length} 条已确认
            </span>
          </div>
          <div className="card-b">
            {confirmed.length === 0 ? (
              <div className="empty" style={{ padding: 24 }}>
                <h3>还没有已确认的需求</h3>
                <p>先去需求库把候选需求逐条确认，再回来生成用例。</p>
                <div className="row">
                  <Link className="btn" href="/requirements">
                    去需求库
                  </Link>
                </div>
              </div>
            ) : (
              <>
                <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <button
                    className="btn sm ghost"
                    type="button"
                    onClick={() =>
                      setSelected(selected.size === confirmed.length ? new Set() : new Set(confirmed.map((r) => r.id)))
                    }
                  >
                    {selected.size === confirmed.length ? "取消全选" : "全选"}
                  </button>
                  <span className="st idle">不勾选＝为全部已确认需求生成</span>
                </div>
                <div className="picker">
                  {confirmed.map((r) => (
                    <label key={r.id} className={`pick${selected.has(r.id) ? " on" : ""}`}>
                      <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleReq(r.id)} />
                      <span className="pid">{r.id}</span>
                      <span>{r.title}</span>
                    </label>
                  ))}
                </div>
                <div className="case-foot" style={{ borderTop: 0, marginTop: 10, paddingTop: 0 }}>
                  <span className="st idle">会覆盖选中需求已有的用例（含已审核的）</span>
                  <div className="sp" />
                  <button className="btn ghost" type="button" disabled={generating} onClick={() => setGenOpen(false)}>
                    取消
                  </button>
                  <button className="btn primary" type="button" disabled={generating} onClick={generate}>
                    {generating
                      ? `生成中… ${elapsed}s`
                      : `为 ${selected.size || confirmed.length} 条需求生成`}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}

      {message ? <div className={`extract-status ${message.kind}`}>{message.text}</div> : null}

      {feed.source === "mock" ? (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="empty">
            <div className="ic">
              <Icon name="alert" size={20} />
            </div>
            <h3>后端没有连上</h3>
            <p>启动 FastAPI（8000）后刷新，用例列表与生成都会基于真实数据。</p>
          </div>
        </div>
      ) : (
        <>
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
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-2)" }}>
              <input className="cb" type="checkbox" checked={allChecked} onChange={toggleAllCases} />
              全选当前列表
            </label>
            <span className="st idle">生成只提候选，审核由人确认</span>
          </div>

          {selectedCases.size > 0 ? (
            <div className="bulkbar">
              <b>已选 {selectedCases.size} 条</b>
              <span style={{ opacity: 0.6 }}>·</span>
              <button className="btn sm" type="button" disabled={batchBusy} onClick={() => batchReview("已审核")}>
                批量通过
              </button>
              <button
                className="btn sm danger"
                type="button"
                disabled={batchBusy}
                onClick={() => batchReview("已驳回")}
              >
                批量驳回
              </button>
              <div className="sp" />
              <button className="btn sm ghost" type="button" onClick={() => setSelectedCases(new Set())}>
                取消选择
              </button>
            </div>
          ) : null}

          {rows.length === 0 ? (
            <div className="card">
              <div className="empty">
                <div className="ic">
                  <Icon name="flask" size={20} />
                </div>
                <h3>{feed.total === 0 ? "还没有用例" : "这一类没有用例"}</h3>
                <p>
                  {feed.total === 0
                    ? "点右上角「生成用例」，选择已确认需求后用大模型生成候选。"
                    : "换一个筛选条件看看。"}
                </p>
                {feed.total === 0 ? (
                  <div className="row">
                    <button className="btn primary" type="button" onClick={() => setGenOpen(true)}>
                      生成用例
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            <div>
              {rows.map((c) => {
                const last = latestByTc.get(c.tc_id);
                return (
                  <article
                    className="case-card"
                    key={c.tc_id}
                    style={selectedCases.has(c.tc_id) ? { borderColor: "var(--accent)" } : undefined}
                  >
                    <div className="case-head">
                      <input
                        className="cb"
                        type="checkbox"
                        aria-label={`选择 TC-${c.tc_id}`}
                        checked={selectedCases.has(c.tc_id)}
                        onChange={() => toggleCase(c.tc_id)}
                      />
                      <span className="chip mono">TC-{String(c.tc_id).padStart(3, "0")}</span>
                      <span className={`chip ${TYPE_CHIP[c.test_type] ?? ""}`}>
                        {TYPE_LABEL[c.test_type] ?? c.test_type}
                      </span>
                      <span className="case-title">{c.title}</span>
                      <span className={`st ${STATUS_CHIP[c.status] ?? "idle"}`}>
                        <span className="dot" />
                        {c.status}
                      </span>
                    </div>

                    <div className="case-grid">
                      <div>
                        <div className="lb">前置条件</div>
                        <ul>
                          {c.preconditions.length ? (
                            c.preconditions.map((p, i) => <li key={i}>{p}</li>)
                          ) : (
                            <li style={{ listStyle: "none", color: "var(--text-3)" }}>无</li>
                          )}
                        </ul>
                      </div>
                      <div>
                        <div className="lb">操作步骤</div>
                        <ol>
                          {c.steps.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ol>
                      </div>
                      <div>
                        <div className="lb">预期结果</div>
                        <p>{c.expected_result}</p>
                      </div>
                    </div>

                    <div className="case-foot">
                      {c.req_id ? (
                        <Link className="chip accent" href={`/requirements?open=${c.req_id}`}>
                          {c.req_id}
                        </Link>
                      ) : null}
                      {last ? (
                        <span
                          className={`st ${RESULT_CHIP[last.result] ?? "idle"}`}
                          title={`${last.tester ? `执行人 ${last.tester}` : "未填执行人"}${last.comments ? ` · ${last.comments}` : ""}`}
                        >
                          <span className="dot" />
                          最近执行：{RESULT_LABEL[last.result] ?? last.result}
                          {last.executed_at ? ` · ${formatApiTime(last.executed_at).slice(0, 10)}` : ""}
                        </span>
                      ) : (
                        <span className="st idle">未执行</span>
                      )}
                      <div className="sp" />
                      <button
                        className="btn sm ghost"
                        type="button"
                        disabled={busyId === c.tc_id}
                        onClick={() => {
                          setExecTarget(c);
                          setExecOpen(true);
                        }}
                      >
                        <Icon name="flask" size={13} />
                        记录执行
                      </button>
                      <button
                        className="btn sm ghost"
                        type="button"
                        onClick={() => {
                          setEditing(c);
                          setFormOpen(true);
                        }}
                      >
                        <Icon name="doc" size={13} />
                        编辑
                      </button>
                      <button
                        className="btn sm"
                        type="button"
                        disabled={busyId === c.tc_id || c.status === "已审核"}
                        onClick={() => review(c, "已审核")}
                      >
                        审核通过
                      </button>
                      <button
                        className="btn sm danger"
                        type="button"
                        disabled={busyId === c.tc_id || c.status === "已驳回"}
                        onClick={() => review(c, "已驳回")}
                      >
                        驳回
                      </button>
                      {c.status !== "已生成" ? (
                        <button
                          className="btn sm ghost"
                          type="button"
                          disabled={busyId === c.tc_id}
                          onClick={() => review(c, "已生成")}
                        >
                          撤回
                        </button>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}

      <ImportDialog
        open={importOpen}
        kind="cases"
        projectId={1}
        onClose={() => setImportOpen(false)}
        onSaved={() => router.refresh()}
      />

      <ExecutionForm
        open={execOpen}
        projectId={1}
        testCase={execTarget}
        onClose={() => setExecOpen(false)}
        onSaved={() => router.refresh()}
      />

      <CaseForm
        open={formOpen}
        projectId={1}
        initial={editing}
        onClose={() => setFormOpen(false)}
        onSaved={() => router.refresh()}
      />
    </section>
  );
}
