import Link from "next/link";
import type { SearchFeed } from "@/lib/data";

const REQ_STATUS_LABEL: Record<string, string> = {
  confirmed: "已确认",
  unconfirmed: "未确认",
  rejected: "已驳回",
};
const REQ_STATUS_CLS: Record<string, string> = {
  confirmed: "ok",
  unconfirmed: "idle",
  rejected: "danger",
};
const KIND_LABEL: Record<string, string> = {
  ambiguous: "模糊表达",
  conflict: "需求冲突",
  missing_acceptance: "缺验收条件",
};
const CASE_STATUS_CLS: Record<string, string> = {
  已生成: "idle",
  已审核: "ok",
  已驳回: "danger",
  已执行: "accent",
};

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="card-h">
        <span className="t">{title}</span>
        <span className="m">{count} 条</span>
      </div>
      <div className="card-b">{children}</div>
    </div>
  );
}

function Row({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "9px 0",
        borderBottom: "1px solid var(--line)",
      }}
    >
      {children}
    </Link>
  );
}

export function SearchView({ feed }: { feed: SearchFeed }) {
  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">搜索</div>
          <h1 className="page-title">搜索结果</h1>
          <div className="page-sub">
            关键词「{feed.query}」 · 需求 {feed.requirements.length} 条 · 用例 {feed.cases.length} 条 ·
            质量问题 {feed.quality.length} 条
          </div>
        </div>
      </div>

      <Section title="需求" count={feed.requirements.length}>
        {feed.requirements.length === 0 ? (
          <div className="empty" style={{ padding: 20 }}>
            <p>没有匹配的需求。</p>
          </div>
        ) : (
          feed.requirements.map((r) => (
            <Row key={r.id} href={`/requirements?open=${encodeURIComponent(r.id)}`}>
              <span style={{ fontSize: 11.5, color: "var(--text-3)", width: 66 }}>{r.id}</span>
              <span style={{ fontWeight: 550 }}>{r.title}</span>
              <span style={{ flex: 1, fontSize: 12, color: "var(--text-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {r.desc}
              </span>
              <span className={`chip ${REQ_STATUS_CLS[r.status] ?? ""}`}>
                {REQ_STATUS_LABEL[r.status] ?? r.status}
              </span>
            </Row>
          ))
        )}
      </Section>

      <Section title="测试用例" count={feed.cases.length}>
        {feed.cases.length === 0 ? (
          <div className="empty" style={{ padding: 20 }}>
            <p>没有匹配的用例。</p>
          </div>
        ) : (
          feed.cases.map((c) => (
            <Row key={c.tc_id} href="/cases">
              <span style={{ fontSize: 11.5, color: "var(--text-3)", width: 66 }}>
                TC-{String(c.tc_id).padStart(3, "0")}
              </span>
              <span style={{ fontWeight: 550 }}>{c.title}</span>
              <span style={{ flex: 1, fontSize: 12, color: "var(--text-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {c.expected_result}
              </span>
              <span className={`chip ${CASE_STATUS_CLS[c.status] ?? ""}`}>{c.status}</span>
            </Row>
          ))
        )}
      </Section>

      <Section title="质量问题" count={feed.quality.length}>
        {feed.quality.length === 0 ? (
          <div className="empty" style={{ padding: 20 }}>
            <p>没有匹配的质量问题。</p>
          </div>
        ) : (
          feed.quality.map((issue) => (
            <Row key={issue.fingerprint || issue.issue_id} href="/quality">
              <span style={{ fontSize: 11.5, color: "var(--text-3)", width: 66 }}>
                {KIND_LABEL[issue.kind] ?? issue.kind}
              </span>
              <span style={{ fontWeight: 550 }}>{issue.title}</span>
              <span style={{ flex: 1, fontSize: 12, color: "var(--text-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {issue.req_ids.join(" / ")}
              </span>
              <span className="chip">{issue.decision === "open" ? "待处置" : "已裁决"}</span>
            </Row>
          ))
        )}
      </Section>
    </section>
  );
}
