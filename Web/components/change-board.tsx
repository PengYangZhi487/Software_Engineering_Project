"use client";

import Link from "next/link";
import type { DiffFeed } from "@/lib/server";
import { Icon } from "./icon";

const KIND_META: Record<string, { label: string; chip: string }> = {
  changed: { label: "修改", chip: "warn" },
  added: { label: "新增", chip: "ok" },
  removed: { label: "删除", chip: "danger" },
};

export function ChangeBoard({ feed }: { feed: DiffFeed }) {
  if (!feed.available || !feed.data) {
    const mock = feed.source === "mock";
    return (
      <section className="view active">
        <div className="view-head">
          <div>
            <div className="eyebrow">STEP 07 · 变更</div>
            <h1 className="page-title">版本比对与影响</h1>
            <div className="page-sub">两版文档按段落对齐，差异落到需求条目，再查受影响的用例。</div>
          </div>
        </div>

        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name={mock ? "alert" : "diff"} size={20} />
            </div>
            <h3>{mock ? "后端没有连上" : "还没有第二个版本文档"}</h3>
            <p>
              {mock
                ? feed.message ?? "启动 FastAPI（8000）后刷新本页。"
                : "上传 V1.1（比如把容量从 50 改成 60、退课窗口从 2 周拉长到 4 周），这里会给出左右对照与受影响用例。"}
            </p>
            <div className="row">
              <Link className="btn primary" href="/document?upload=1">
                上传新版本
              </Link>
              <Link className="btn ghost" href="/document">
                看当前文档
              </Link>
            </div>
          </div>
        </div>
      </section>
    );
  }

  const { base, target, summary, changes } = feed.data;

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 07 · 变更</div>
          <h1 className="page-title">版本比对与影响</h1>
          <div className="page-sub">
            {base.version} → {target.version} · 段落级精确比对，变更条目再关联到需求与用例
          </div>
        </div>
        <div className="head-actions">
          <Link className="btn" href="/document?upload=1">
            <Icon name="upload" size={13} />
            上传新版本
          </Link>
        </div>
      </div>

      <div className="strip">
        <div className="metric">
          <div className="k">变更条目</div>
          <div className="v">
            {summary.changed + summary.added + summary.removed}
            <small>处</small>
          </div>
          <div className="d">
            修改 {summary.changed} · 新增 {summary.added} · 删除 {summary.removed}
          </div>
        </div>
        <div className="metric">
          <div className="k">受影响需求</div>
          <div className="v">
            {summary.affected_requirements}
            <small>条</small>
          </div>
          <div className="d">变更段落映射到的需求</div>
        </div>
        <div className="metric">
          <div className="k">关联用例</div>
          <div className="v">
            {summary.affected_cases}
            <small>条</small>
          </div>
          <div className="d">需要人工复核，不等于必须修改</div>
        </div>
        <div className="metric">
          <div className="k">文档</div>
          <div className="v" style={{ fontSize: 15, lineHeight: "34px" }}>
            {base.version} → {target.version}
          </div>
          <div className="d">{base.filename} → {target.filename}</div>
        </div>
      </div>

      <div className="notice warn" style={{ marginTop: 14 }}>
        <Icon name="alert" size={14} style={{ flex: "none", marginTop: 1 }} />
        <div>
          这里列的是「关联影响」——用例关联了变更需求，因此需要检查；是否真的需要改用例，由人判断（关联 ≠ 实际影响）。
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        {changes.map((c) => {
          const meta = KIND_META[c.kind] ?? KIND_META.changed;
          return (
            <article className="diff-card" key={c.change_id}>
              <div className="diff-head">
                <span className="chip mono">{c.change_id}</span>
                <span className={`chip ${meta.chip}`}>{meta.label}</span>
                <span className="diff-para">
                  {c.base_para !== null ? `¶${c.base_para}` : "—"} → {c.target_para !== null ? `¶${c.target_para}` : "—"}
                </span>
                <div style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {c.req_ids.map((rid) => (
                    <Link key={rid} className="chip accent" href={`/requirements?open=${rid}`}>
                      {rid}
                    </Link>
                  ))}
                </div>
              </div>

              <div className="diff-grid">
                <div>
                  <div className="lb">旧版</div>
                  <p className="diff-text old">{c.base_text || "（无）"}</p>
                </div>
                <div>
                  <div className="lb">新版</div>
                  <p className="diff-text new">{c.target_text || "（无）"}</p>
                </div>
              </div>

              {(c.removed_numbers.length > 0 || c.added_numbers.length > 0) && (
                <div className="diff-nums">
                  {c.removed_numbers.map((n) => (
                    <span key={`r-${n}`} className="chip danger">
                      − {n}
                    </span>
                  ))}
                  {c.added_numbers.map((n) => (
                    <span key={`a-${n}`} className="chip ok">
                      + {n}
                    </span>
                  ))}
                </div>
              )}

              {c.cases.length > 0 ? (
                <div className="diff-cases">
                  <span className="lb" style={{ marginRight: 8 }}>关联用例</span>
                  {c.cases.map((tc) => (
                    <Link key={tc.tc_id} className="chip" href={`/cases`}>
                      TC-{String(tc.tc_id).padStart(3, "0")} · {tc.status}
                    </Link>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
