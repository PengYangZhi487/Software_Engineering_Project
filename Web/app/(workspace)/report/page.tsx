"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/icon";
import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { saveExportFile, type SavedExport } from "@/lib/api";
import { loadReport } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

function pct(part: number, total: number) {
  return total ? Math.round((part / total) * 100) : 0;
}

export default function ReportPage() {
  const { projectId, ready } = useCurrentProject();
  const { data: feed, loading, error } = useApi(() => loadReport(projectId), [projectId]);
  const [saving, setSaving] = useState<"xlsx" | "csv" | null>(null);
  const [saved, setSaved] = useState<SavedExport | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (!ready || loading || !feed) return <Loading title="正在生成质量报告…" />;
  if (error || !feed.data) return <Offline message={error ?? feed.error} />;

  const { project, documents, counts, generated_at } = feed.data;
  const issueTotal = Math.max(counts.issues, 1);
  const caseTotal = Math.max(counts.cases, 1);

  async function runExport(format: "xlsx" | "csv") {
    if (!feed?.data) return;
    setSaving(format);
    setSaved(null);
    setSaveError(null);
    try {
      const result = await saveExportFile(feed.data.project.project_id, "report", format);
      setSaved(result);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setSaving(null);
    }
  }

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
          <button
            className="btn primary"
            type="button"
            disabled={saving !== null}
            onClick={() => void runExport("xlsx")}
          >
            <Icon name="down" />
            {saving === "xlsx" ? "导出中…" : "导出 Excel"}
          </button>
          <button className="btn" type="button" disabled={saving !== null} onClick={() => void runExport("csv")}>
            {saving === "csv" ? "导出中…" : "导出 CSV"}
          </button>
        </div>
      </div>

      {saved ? (
        <div className="extract-status ok" style={{ marginTop: 10, wordBreak: "break-all" }}>
          已导出到：{saved.path}（{Math.round(saved.size / 1024)} KB）
          <button
            type="button"
            className="btn sm ghost"
            style={{ marginLeft: 8 }}
            onClick={() => void navigator.clipboard?.writeText(saved.path)}
          >
            复制路径
          </button>
        </div>
      ) : null}
      {saveError ? (
        <div className="extract-status err" style={{ marginTop: 10 }}>{saveError}</div>
      ) : null}

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
            <span className="m">Excel · CSV</span>
          </div>
          <div className="card-b" style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.9 }}>
            <div>· Excel 含四个 Sheet：概览、需求清单、测试用例执行表（实际结果 / comments / 签名）、覆盖矩阵；</div>
            <div>· CSV 仍是汇总、需求清单、质量问题、测试用例四段；</div>
            <div>· 覆盖率口径：至少关联一条已审核用例的已确认需求 / 已确认需求总数；</div>
            <div>· 数字与页面同源（同一个 _build()），Excel 直接打开不乱码；</div>
            <div style={{ marginTop: 8 }}>
              <button className="btn sm" type="button" disabled={saving !== null} onClick={() => void runExport("xlsx")}>
                {saving === "xlsx" ? "导出中…" : "导出 Excel"}
              </button>
              <button
                className="btn sm ghost"
                type="button"
                disabled={saving !== null}
                onClick={() => void runExport("csv")}
                style={{ marginLeft: 8 }}
              >
                {saving === "csv" ? "导出中…" : "导出 CSV"}
              </button>
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
