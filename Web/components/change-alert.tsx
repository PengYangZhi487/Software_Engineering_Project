"use client";

/**
 * 变更提醒：文档改版（两个及以上版本、且有段落级改动）后提示受影响的需求与用例。
 *
 * 数据直接复用 lib/data.ts 的 loadDiff（服务端 /api/projects/{pid}/document-diff）：
 * - 文档工作台、总览：compact 卡片（受影响需求/用例数 + 去 /changes）
 * - 变更页顶部：detailed 面板（额外列出受影响的用例，给出「建议重跑」清单）
 *
 * 关闭状态只记在 sessionStorage（本次会话），并且按「目标文档 + 改动数」做签名：
 * 上传了新版本 / 改动数变了会重新提醒，不会因为上次关过就永远不提示。
 */
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { DiffCase, DiffFeed } from "@/lib/data";
import { Icon } from "./icon";

const STORAGE_KEY = "ratgp-change-alert-dismissed";

/** 提醒签名：没有两版文档 / 没有改动时返回 null（不提醒）。 */
export function changeSignature(feed: DiffFeed | null): string | null {
  if (!feed?.available || !feed.data) return null;
  const { target, summary } = feed.data;
  if (summary.changed <= 0) return null;
  return `${target.doc_id}:${summary.changed}:${summary.added}:${summary.removed}`;
}

export function ChangeAlert({
  feed,
  variant = "compact",
}: {
  feed: DiffFeed | null;
  variant?: "compact" | "detailed";
}) {
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      setDismissed(sessionStorage.getItem(STORAGE_KEY));
    } catch {
      setDismissed(null);
    }
    setReady(true);
  }, []);

  const signature = changeSignature(feed);

  const affectedCases = useMemo<DiffCase[]>(() => {
    if (!feed?.data) return [];
    const map = new Map<number, DiffCase>();
    for (const change of feed.data.changes) {
      for (const tc of change.cases) map.set(tc.tc_id, tc);
    }
    return [...map.values()];
  }, [feed]);

  // 首帧不渲染（还没读 sessionStorage），避免「已经关掉了又闪一下」
  if (!ready || !feed || !feed.data || !signature) return null;
  if (variant === "compact" && dismissed === signature) return null;

  const { summary, base, target } = feed.data;
  // 变更页的详细面板是常驻信息，不参与「本次会话不再提示」
  const canDismiss = variant === "compact";

  function dismiss() {
    if (!signature) return;
    try {
      sessionStorage.setItem(STORAGE_KEY, signature);
    } catch {
      /* 隐私模式忽略 */
    }
    setDismissed(signature);
  }

  return (
    <div className="card change-alert" style={{ borderColor: "var(--warn)" }}>
      <div className="card-h">
        <Icon name="alert" size={14} style={{ color: "var(--warn)" }} />
        <span className="t">文档已改版：{base.version} → {target.version}</span>
        <span className="m">变更影响</span>
        {canDismiss ? (
          <button
            className="btn icon ghost"
            type="button"
            title="本次会话不再提示"
            aria-label="关闭变更提醒"
            onClick={dismiss}
          >
            <Icon name="x" size={14} />
          </button>
        ) : null}
      </div>

      <div className="card-b" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.8 }}>
          本次改版共 <b style={{ color: "var(--text)" }}>{summary.changed}</b> 处段落改动（新增{" "}
          {summary.added} / 删除 {summary.removed}）
          {summary.affected_requirements > 0 ? (
            <>
              ，影响 <b style={{ color: "var(--text)" }}>{summary.affected_requirements}</b> 条需求、
              <b style={{ color: "var(--text)" }}>{summary.affected_cases}</b> 条用例。
            </>
          ) : (
            <>；这些改动还没有关联到需求条目（需求未按段落匹配，可先到「文档」页抽取需求）。</>
          )}
          <br />
          <span style={{ color: "var(--text-3)", fontSize: 11.5 }}>
            关联不等于必须修改：需要人工判断原有用例的预期结果是否还成立。
          </span>
        </div>

        {variant === "detailed" ? (
          affectedCases.length > 0 ? (
            <div>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 6 }}>
                建议优先重跑这些用例（关联了变更段落）
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {affectedCases.slice(0, 12).map((tc) => (
                  <Link key={tc.tc_id} className="chip" href="/cases">
                    TC-{String(tc.tc_id).padStart(3, "0")} · {tc.status}
                  </Link>
                ))}
                {affectedCases.length > 12 ? (
                  <span className="chip">+{affectedCases.length - 12}</span>
                ) : null}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>
              还没有用例关联到本次变更段落——可以先去「用例」页按已确认需求生成。
            </div>
          )
        ) : null}

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link className="btn sm primary" href="/changes">
            <Icon name="diff" size={13} />
            查看变更影响
          </Link>
          {variant === "detailed" && affectedCases.length > 0 ? (
            <Link className="btn sm" href="/cases">
              <Icon name="flask" size={13} />
              去重跑用例
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}
