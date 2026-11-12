"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { hitWords } from "@/lib/quality";
import type { DataSource, Requirement } from "@/lib/types";
import { Icon } from "./icon";

type Filter = "all" | "unconfirmed" | "confirmed" | "rejected" | "ambiguous";
type ApiStatus = "未审核" | "已确认" | "已驳回";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "unconfirmed", label: "未确认" },
  { id: "confirmed", label: "已确认" },
  { id: "rejected", label: "已驳回" },
  { id: "ambiguous", label: "模糊" },
];

const STATUS_META: Record<Requirement["status"], { label: string; cls: string }> = {
  confirmed: { label: "已确认", cls: "ok" },
  unconfirmed: { label: "未确认", cls: "idle" },
  rejected: { label: "已驳回", cls: "danger" },
};

function matchFilter(r: Requirement, f: Filter) {
  if (f === "unconfirmed") return r.status === "unconfirmed";
  if (f === "confirmed") return r.status === "confirmed";
  if (f === "rejected") return r.status === "rejected";
  if (f === "ambiguous") return r.risks.includes("ambiguous");
  return true;
}

export function ReqExplorer({
  items,
  source,
  initialQuery,
  initialOpen = null,
}: {
  items: Requirement[];
  source: DataSource;
  initialQuery: string;
  initialOpen?: string | null;
}) {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>("all");
  const [q, setQ] = useState(initialQuery);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [openId, setOpenId] = useState<string | null>(initialOpen);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => setQ(initialQuery), [initialQuery]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenId(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function flash(msg: string) {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2200);
  }

  const rows = useMemo(() => {
    const kw = q.trim().toLowerCase();
    return items.filter((r) => {
      if (kw && !`${r.id} ${r.title} ${r.desc}`.toLowerCase().includes(kw)) return false;
      return matchFilter(r, filter);
    });
  }, [filter, q, items]);

  const counts = useMemo(
    () =>
      ({
        all: items.length,
        unconfirmed: items.filter((r) => r.status === "unconfirmed").length,
        confirmed: items.filter((r) => r.status === "confirmed").length,
        rejected: items.filter((r) => r.status === "rejected").length,
        ambiguous: items.filter((r) => r.risks.includes("ambiguous")).length,
      }) as Record<Filter, number>,
    [items],
  );

  const open = openId ? items.find((r) => r.id === openId) ?? null : null;
  const allChecked = rows.length > 0 && rows.every((r) => selected.has(r.id));

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected(allChecked ? new Set() : new Set(rows.map((r) => r.id)));
  }

  async function patchStatus(ids: string[], status: ApiStatus) {
    if (source !== "api") {
      flash("后端未连接，改动不会保存");
      return false;
    }
    setBusy(true);
    try {
      for (const id of ids) {
        const res = await fetch(`${API_BASE}/api/requirements/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        });
        if (!res.ok) {
          const detail = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(detail?.detail ?? `HTTP ${res.status}`);
        }
      }
      flash(ids.length > 1 ? `已更新 ${ids.length} 条` : `已更新 ${ids[0]}`);
      router.refresh();
      return true;
    } catch (err) {
      flash(err instanceof Error ? err.message : "保存失败");
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 03 · 需求</div>
          <h1 className="page-title">
            需求库
            {source === "mock" ? (
              <span className="chip warn" title="后端未连接，当前展示示例数据">
                示例数据
              </span>
            ) : null}
          </h1>
          <div className="page-sub">AI 抽取的候选需求，逐条确认后进入追踪与用例生成。</div>
        </div>
        <div className="head-actions">
          <button className="btn" type="button" onClick={() => flash("导出将在 P8 接入")}>
            <Icon name="down" />导出
          </button>
          <button className="btn primary" type="button" onClick={() => flash("手动新建在 P3.1 接入")}>
            <Icon name="plus" />新建需求
          </button>
        </div>
      </div>

      <div className="toolbar">
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
        <span className="st idle">
          <Icon name="filter" size={13} />
          点击行查看详情 · 可确认 / 驳回
        </span>
      </div>

      {selected.size > 0 ? (
        <div className="bulkbar">
          <b>已选 {selected.size} 条</b>
          <span style={{ opacity: 0.6 }}>·</span>
          <button
            className="btn sm"
            type="button"
            disabled={busy}
            onClick={async () => {
              if (await patchStatus([...selected], "已确认")) setSelected(new Set());
            }}
          >
            批量确认
          </button>
          <button
            className="btn sm danger"
            type="button"
            disabled={busy}
            onClick={async () => {
              if (await patchStatus([...selected], "已驳回")) setSelected(new Set());
            }}
          >
            批量驳回
          </button>
          <div className="sp" />
          <button className="btn sm ghost" type="button" onClick={() => setSelected(new Set())}>
            取消选择
          </button>
        </div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="col-cb">
                <input className="cb" type="checkbox" aria-label="全选" checked={allChecked} onChange={toggleAll} />
              </th>
              <th style={{ width: 78 }}>编号</th>
              <th>标题</th>
              <th style={{ width: 88 }}>类型</th>
              <th style={{ width: 62 }}>验收</th>
              <th style={{ width: 84 }}>风险</th>
              <th style={{ width: 92 }}>状态</th>
              <th style={{ width: 62 }}>来源</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8}>
                  <div className="empty" style={{ padding: 40 }}>
                    <h3>没有匹配的需求</h3>
                    <p>换个筛选条件，或清空搜索词。</p>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((r) => {
                const meta = STATUS_META[r.status];
                return (
                  <tr key={r.id} className={selected.has(r.id) ? "sel" : ""} onClick={() => setOpenId(r.id)}>
                    <td className="col-cb">
                      <input
                        className="cb"
                        type="checkbox"
                        aria-label={`选择 ${r.id}`}
                        checked={selected.has(r.id)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => toggle(r.id)}
                      />
                    </td>
                    <td className="id">{r.id}</td>
                    <td className="tt">{r.title}</td>
                    <td>
                      <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                        {r.type === "functional" ? "功能" : "非功能"}
                      </span>
                    </td>
                    <td className="tnum">{r.acc.length}</td>
                    <td>
                      {r.risks.length ? (
                        <span className="chip warn">模糊</span>
                      ) : (
                        <span style={{ color: "var(--text-3)", fontSize: 11.5 }}>—</span>
                      )}
                    </td>
                    <td>
                      <span className={`st ${meta.cls}`}>
                        <span className="dot" />
                        {meta.label}
                      </span>
                    </td>
                    <td className="src">¶{r.para}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className={`scrim${open ? " on" : ""}`} onClick={() => setOpenId(null)} />
      <aside className={`drawer${open ? " on" : ""}`} aria-hidden={!open}>
        {open ? (
          <DrawerBody
            req={open}
            busy={busy}
            onClose={() => setOpenId(null)}
            onAct={async (status) => {
              if (await patchStatus([open.id], status)) setOpenId(null);
            }}
          />
        ) : null}
      </aside>

      <div className={`toast${toast ? " on" : ""}`}>{toast}</div>
    </>
  );
}

function DrawerBody({
  req,
  busy,
  onClose,
  onAct,
}: {
  req: Requirement;
  busy: boolean;
  onClose: () => void;
  onAct: (status: ApiStatus) => void;
}) {
  const words = hitWords(`${req.title} ${req.desc}`);
  const meta = STATUS_META[req.status];

  const primary: { label: string; status: ApiStatus } =
    req.status === "confirmed" ? { label: "撤回", status: "未审核" } : { label: "确认", status: "已确认" };
  const secondary: { label: string; status: ApiStatus } =
    req.status === "rejected" ? { label: "恢复", status: "未审核" } : { label: "驳回", status: "已驳回" };

  return (
    <>
      <div className="dh">
        <div>
          <div className="id">{req.id}</div>
          <div className="ti">{req.title}</div>
        </div>
        <button className="btn icon ghost x" type="button" onClick={onClose} aria-label="关闭">
          <Icon name="x" size={15} />
        </button>
      </div>

      <div className="db">
        <div className="dsec" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <span className="chip">{req.type === "functional" ? "功能需求" : "非功能需求"}</span>
          <span className={`chip ${meta.cls}`}>
            <span className="dot" />
            {meta.label}
          </span>
          <span className="chip">验收 {req.acc.length} 条</span>
        </div>

        {words.length > 0 ? (
          <div className="notice warn">
            <Icon name="alert" size={14} style={{ flex: "none", marginTop: 1 }} />
            <div>命中模糊表达：{words.map((w) => `「${w}」`).join(" ")} —— 建议补充可量化的指标后再确认。</div>
          </div>
        ) : null}

        <div className="dsec" style={{ marginTop: 14 }}>
          <div className="lb">需求描述</div>
          <p>{req.desc}</p>
        </div>

        <div className="dsec">
          <div className="lb">验收条件</div>
          <ol className="aclist">
            {req.acc.map((a, i) => (
              <li key={i}>
                <i>{String(i + 1).padStart(2, "0")}</i>
                <span>{a}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="dsec">
          <div className="lb">来源段落</div>
          <div className="quote">
            <span className="q">
              ¶{req.para} · 相似度 {req.ratio.toFixed(2)}
            </span>
            {req.raw || "—"}
          </div>
        </div>
      </div>

      <div className="df">
        <button
          className="btn primary"
          type="button"
          style={{ flex: 1 }}
          disabled={busy}
          onClick={() => onAct(primary.status)}
        >
          <Icon name="check" size={14} />
          {primary.label}
        </button>
        <button
          className="btn danger"
          type="button"
          style={{ flex: 1 }}
          disabled={busy}
          onClick={() => onAct(secondary.status)}
        >
          {secondary.label}
        </button>
      </div>
    </>
  );
}
