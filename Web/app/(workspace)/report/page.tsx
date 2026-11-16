import Link from "next/link";
import { Icon } from "@/components/icon";
import { API_BASE } from "@/lib/api";
import { loadReport } from "@/lib/server";

export const metadata = { title: "质量报告 · RATGP" };

function pct(part: number, total: number) {
  return total ? Math.round((part / total) * 100) : 0;
}

export default async function ReportPage() {
  const feed = await loadReport(1);

  if (!feed.data) {
    return (
      <section className="view active">
        <div className="view-head">
          <div>
            <div className="eyebrow">STEP 08 · 报告</div>
            <h1 className="page-title">质量报告</h1>
            <div className="page-sub">需求、问题、用例与覆盖率的汇总，可导出 CSV。</div>
          </div>
        </div>
        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name="alert" size={20} />
            </div>
            <h3>后端没有连上</h3>
            <p>{feed.error ?? "启动 FastAPI（8000）后刷新本页。"}</p>
            <div className="row">
              <a className="btn" href="/report">
                重试
              </a>
            </div>
          </div>
        </div>
      </section>
    );
  }

  const { project, documents, counts, generated_at } = feed.data;
  const exportUrl = `${API_BASE}/api/projects/${project.project_id}/report/export?format=csv`;
  const issueTotal = Math.max(counts.issues, 1);
  const caseTotal = Math.max(counts.cases, 1);

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 08 · 报告</div>
          <h1 className="page-title">质量报告</h1>
          <div className="page-sub">
            {project.project_name} · 生成于 {generated_at} · 导出值与页面同源
          </div>
        </div>
        <div className="head-actions">
          <a className="btn primary" href={exportUrl} download>
            <Icon name="down" />
            下载 CSV
          </a>
        </div>
      </div>

      <div className="strip">
        <div className="metric">
          <div className="k">需求总数</div>
          <div className="v">
            {counts.requirements}
            <small>条</small>
          </div>
          <div className="d">
            已确认 {counts.confirmed} · 未审核 {counts.pending}
          </div>
        </div>
        <div className="metric">
          <div className="k">已确认</div>
          <div className="v">
            {counts.confirmed}
            <small>/ {counts.requirements}</small>
          </div>
          <div className="d">
            <b>{pct(counts.confirmed, counts.requirements)}%</b> 确认率
          </div>
        </div>
        <div className="metric">
          <div className="k">质量问题</div>
          <div className="v">
            {counts.issues}
            <small>条</small>
          </div>
          <div className="d">
            模糊 {counts.ambiguous} · 冲突 {counts.conflict}
          </div>
        </div>
        <div className="metric">
          <div className="k">用例覆盖</div>
          <div className="v">
            {counts.coverage_pct}
            <small>%</small>
          </div>
          <div className="d">
            {counts.covered_requirements} / {counts.confirmed} 条已确认需求
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-h">
            <span className="t">问题分布</span>
            <span className="m">{counts.issues} 条</span>
          </div>
          <div className="card-b dist">
            <div className="dist-row">
              <span>模糊表达</span>
              <span className="bar">
                <i style={{ width: `${(counts.ambiguous / issueTotal) * 100}%`, background: "var(--warn)" }} />
              </span>
              <span className="tnum">{counts.ambiguous}</span>
            </div>
            <div className="dist-row">
              <span>需求冲突</span>
              <span className="bar">
                <i style={{ width: `${(counts.conflict / issueTotal) * 100}%`, background: "var(--danger)" }} />
              </span>
              <span className="tnum">{counts.conflict}</span>
            </div>
            <div className="dist-row">
              <span>缺验收条件</span>
              <span className="bar">
                <i style={{ width: `${(counts.missing_acceptance / issueTotal) * 100}%`, background: "var(--text-3)" }} />
              </span>
              <span className="tnum">{counts.missing_acceptance}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <span className="t">用例状态</span>
            <span className="m">{counts.cases} 条</span>
          </div>
          <div className="card-b dist">
            <div className="dist-row">
              <span>已生成</span>
              <span className="bar">
                <i style={{ width: `${(counts.case_generated / caseTotal) * 100}%`, background: "var(--warn)" }} />
              </span>
              <span className="tnum">{counts.case_generated}</span>
            </div>
            <div className="dist-row">
              <span>已审核</span>
              <span className="bar">
                <i style={{ width: `${(counts.case_reviewed / caseTotal) * 100}%`, background: "var(--ok)" }} />
              </span>
              <span className="tnum">{counts.case_reviewed}</span>
            </div>
            <div className="dist-row">
              <span>已驳回</span>
              <span className="bar">
                <i style={{ width: `${(counts.case_rejected / caseTotal) * 100}%`, background: "var(--danger)" }} />
              </span>
              <span className="tnum">{counts.case_rejected}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-h">
            <span className="t">文档版本</span>
            <span className="m">{documents.length} 份</span>
          </div>
          <div className="card-b">
            {documents.length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--text-2)" }}>还没有上传文档。</div>
            ) : (
              documents.map((doc) => (
                <div key={doc.doc_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0" }}>
                  <Icon name="doc" size={15} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 550 }}>{doc.filename}</div>
                    <div style={{ fontSize: 10.5, color: "var(--text-3)" }}>
                      {doc.version} · {doc.paragraphs} 段
                    </div>
                  </div>
                  <span className="chip" style={{ marginLeft: "auto" }}>
                    #{doc.doc_id}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <span className="t">导出说明</span>
            <span className="m">CSV · UTF-8 BOM</span>
          </div>
          <div className="card-b" style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.9 }}>
            <div>· 一个文件包含四段：汇总、需求清单、质量问题、测试用例；</div>
            <div>· 覆盖率口径：至少关联一条已审核用例的已确认需求 / 已确认需求总数；</div>
            <div>· 数字与页面同源（同一个 _build()），Excel 直接打开不乱码；</div>
            <div>· 更多格式（XLSX / 可编辑报告）留到 P8.1。</div>
            <div style={{ marginTop: 8 }}>
              <a className="btn sm" href={exportUrl} download>
                下载 CSV
              </a>
              <Link className="btn sm ghost" href="/trace" style={{ marginLeft: 8 }}>
                核对覆盖率
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
