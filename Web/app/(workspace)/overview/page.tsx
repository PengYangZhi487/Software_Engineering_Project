import Link from "next/link";
import { Icon } from "@/components/icon";
import { loadQuality, loadRequirements } from "@/lib/server";

const ACTIVITY = [
  { t: "10:58", k: "a", x: <>上传 <b>course_selection_v1.docx</b> · V1.0</> },
  { t: "10:59", k: "", x: <>解析完成，<b>52 段</b>，保留段落序号</> },
  { t: "11:00", k: "a", x: <>AI 抽取候选需求，编号由程序生成（CR-001…）</> },
  { t: "11:04", k: "g", x: <>人工逐条确认，进入「已确认」</> },
  { t: "11:06", k: "", x: <>用例生成在 P5，覆盖率在 P6 接入</> },
];

export default async function OverviewPage() {
  const feed = await loadRequirements(1);
  const quality = await loadQuality(1);
  const { items, counts, source, error } = feed;
  const byKind = quality.byKind;
  const ambiguousIssues = byKind.ambiguous ?? 0;
  const conflictIssues = byKind.conflict ?? 0;
  const missingIssues = byKind.missing_acceptance ?? 0;

  const functional = items.filter((r) => r.type === "functional").length;
  const nonFunctional = items.length - functional;
  const confirmRate = counts.total ? Math.round((counts.confirmed / counts.total) * 100) : 0;
  const issueTotal = Math.max(quality.total, 1);

  const steps = [
    { href: "/document", n: "02", name: "文档", val: "1 份 · 52 段", tone: "done" },
    { href: "/requirements", n: "03", name: "需求", val: `${counts.total} 条 · ${counts.confirmed} 已确认`, tone: "now" },
    { href: "/quality", n: "04", name: "质量", val: `${quality.total} 条问题`, tone: quality.total ? "warn" : "" },
    { href: "/cases", n: "05", name: "用例", val: "0 条（P5）", tone: "" },
    { href: "/trace", n: "06", name: "追踪", val: "待接入（P6）", tone: "" },
    { href: "/changes", n: "07", name: "变更", val: "0 组对比", tone: "" },
    { href: "/report", n: "08", name: "报告", val: "未生成", tone: "" },
  ];

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">PROJECT · 需求工程</div>
          <h1 className="page-title">
            校园选课系统 <span className="ver">V1.0</span>
            {source === "mock" ? (
              <span className="chip warn" title={error ?? "后端未连接，当前展示示例数据"}>
                示例数据
              </span>
            ) : null}
          </h1>
          <div className="page-sub">从需求文档到追踪矩阵，一条主线走完。当前停在「需求审核」。</div>
        </div>
        <div className="head-actions">
          <Link className="btn" href="/document">
            <Icon name="upload" />上传文档
          </Link>
          <Link className="btn primary" href="/requirements">
            <Icon name="flask" />去审核需求
          </Link>
          <button className="btn icon" type="button" title="更多操作">
            <Icon name="more" size={15} />
          </button>
        </div>
      </div>

      <div className="strip">
        <div className="metric">
          <div className="k">需求总数</div>
          <div className="v">
            {counts.total}
            <small>条</small>
          </div>
          <div className="d">
            功能 {functional} · 非功能 {nonFunctional}
          </div>
        </div>
        <div className="metric">
          <div className="k">已确认</div>
          <div className="v">
            {counts.confirmed}
            <small>/ {counts.total}</small>
          </div>
          <div className="d">
            <b>{confirmRate}%</b> 确认率 · 待审核 {counts.pending}
          </div>
        </div>
        <div className="metric">
          <div className="k">待处理问题</div>
          <div className="v">
            {quality.total}
            <small>条</small>
          </div>
          <div className="d">
            模糊 {ambiguousIssues} · 冲突 {conflictIssues}
          </div>
        </div>
        <div className="metric">
          <div className="k">用例覆盖</div>
          <div className="v">—</div>
          <div className="d">用例生成在 P5，覆盖率在 P6</div>
        </div>
      </div>

      <div className="card pipe">
        <div className="card-h">
          <span className="t">主线进度</span>
          <span className="m">第 3 步 / 共 7 步</span>
        </div>
        <div className="card-b">
          <div className="steps">
            {steps.map((s) => (
              <Link
                key={s.href}
                href={s.href}
                className={`step${s.tone === "now" ? " now" : ""}${s.tone === "warn" ? " warnstep" : ""}`}
              >
                <div className="n">{s.n}</div>
                <div className="nm">
                  {s.name}
                  {s.tone === "done" ? <span className="dot" style={{ color: "var(--ok)" }} /> : null}
                  {s.tone === "warn" ? <span className="dot" style={{ color: "var(--warn)" }} /> : null}
                </div>
                <div className="val">{s.val}</div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-h">
            <span className="t">接下来要做什么</span>
            <span className="m">4 项</span>
          </div>
          <div className="card-b">
            {[
              {
                n: String(counts.pending),
                title: `审核 ${counts.pending} 条未确认需求`,
                sub: "逐条确认或驳回，编号已由程序生成",
                href: "/requirements",
              },
              {
                n: String(quality.total),
                title: `裁决 ${quality.total} 条质量问题`,
                sub: `模糊 ${ambiguousIssues} · 冲突 ${conflictIssues} · 缺验收 ${missingIssues}`,
                href: "/quality",
              },
              {
                n: String(counts.confirmed),
                title: "给已确认需求生成用例",
                sub: "正常 / 异常 / 边界三类，P5 接入",
                href: "/cases",
              },
              { n: "1", title: "生成质量报告", sub: "覆盖率与问题统计，可复算", href: "/report" },
            ].map((todo) => (
              <Link key={todo.title} href={todo.href} className="todo" style={{ textDecoration: "none" }}>
                <div className="num">{todo.n}</div>
                <div>
                  <div className="tt">{todo.title}</div>
                  <div className="ts">{todo.sub}</div>
                </div>
                <svg className="go" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </Link>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <span className="t">最近活动</span>
            <span className="m">今天</span>
          </div>
          <div className="card-b" style={{ paddingTop: 12 }}>
            {ACTIVITY.map((a) => (
              <div className="act" key={a.t}>
                <div className="time">{a.t}</div>
                <div className={`bd ${a.k}`} />
                <div className="tx">{a.x}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
        <div className="card">
          <div className="card-h">
            <span className="t">问题分布</span>
            <span className="m">{quality.total} 条</span>
          </div>
          <div className="card-b dist">
            <div className="dist-row">
              <span>模糊表达</span>
              <span className="bar">
                <i style={{ width: `${(ambiguousIssues / issueTotal) * 100}%`, background: "var(--warn)" }} />
              </span>
              <span className="tnum">{ambiguousIssues}</span>
            </div>
            <div className="dist-row">
              <span>需求冲突</span>
              <span className="bar">
                <i style={{ width: `${(conflictIssues / issueTotal) * 100}%`, background: "var(--danger)" }} />
              </span>
              <span className="tnum">{conflictIssues}</span>
            </div>
            <div className="dist-row">
              <span>缺验收条件</span>
              <span className="bar">
                <i style={{ width: `${(missingIssues / issueTotal) * 100}%`, background: "var(--text-3)" }} />
              </span>
              <span className="tnum">{missingIssues}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <span className="t">文档版本</span>
            <span className="m">1 份</span>
          </div>
          <div className="card-b" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Icon name="doc" size={16} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 550, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                course_selection_v1.docx
              </div>
              <div style={{ fontSize: 10.5, color: "var(--text-3)" }}>V1.0 · 52 段 · 解析完成</div>
            </div>
            <span className="chip ok" style={{ marginLeft: "auto" }}>
              <span className="dot" />
              就绪
            </span>
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <span className="t">AI 用量</span>
            <span className="m">本月</span>
          </div>
          <div className="card-b">
            <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
              <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-.02em" }}>¥ 3.84</span>
              <span style={{ fontSize: 11, color: "var(--text-3)" }}>/ 预算 ¥50</span>
            </div>
            <div className="bar" style={{ marginTop: 9 }}>
              <i style={{ width: "8%", background: "var(--accent)" }} />
            </div>
            <div style={{ fontSize: 10.5, color: "var(--text-3)", marginTop: 7 }}>38 次调用 · 平均 2.1k tokens</div>
          </div>
        </div>
      </div>
    </section>
  );
}
