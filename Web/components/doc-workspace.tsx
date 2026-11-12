"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";
import type { ApiDocumentMeta, ApiParagraph } from "@/lib/api";
import { formatApiTime } from "@/lib/api";
import type { Requirement } from "@/lib/types";
import { Icon } from "./icon";
import { UploadCard } from "./upload-card";

export function DocWorkspace({
  doc,
  paragraphs,
  apiError,
  requirements,
  initialUploadOpen = false,
  initialExtractOpen = false,
}: {
  doc: ApiDocumentMeta | null;
  paragraphs: ApiParagraph[];
  apiError: string | null;
  requirements: Requirement[];
  initialUploadOpen?: boolean;
  initialExtractOpen?: boolean;
}) {
  const router = useRouter();
  const [uploadOpen, setUploadOpen] = useState(initialUploadOpen);
  const [selected, setSelected] = useState<number | null>(null);
  const [extractOpen, setExtractOpen] = useState(initialExtractOpen);
  const [extracting, setExtracting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [extractMsg, setExtractMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const paperRef = useRef<HTMLDivElement>(null);

  // 抽取期间显示已等待秒数（LLM 通常 10–30s，没有进度条也要让人知道还活着）
  useEffect(() => {
    if (!extracting) return;
    setElapsed(0);
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [extracting]);

  async function runExtract() {
    if (!doc) return;
    setExtracting(true);
    setExtractMsg(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/projects/${doc.project_id}/requirements/extract?replace=true&doc_id=${doc.doc_id}`,
        { method: "POST" },
      );
      const data = (await res.json().catch(() => null)) as
        | { created?: number; detail?: string }
        | null;
      if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`);
      setExtractOpen(false);
      setExtractMsg({
        kind: "ok",
        text: `已抽取 ${data?.created ?? 0} 条需求，编号从 CR-001 起，状态为「未审核」`,
      });
      router.refresh();
    } catch (err) {
      setExtractMsg({ kind: "error", text: err instanceof Error ? err.message : "抽取失败" });
    } finally {
      setExtracting(false);
    }
  }

  const headings = useMemo(() => paragraphs.filter((p) => p.is_heading), [paragraphs]);

  // 标题取第一个 Heading 1，正文里不再重复渲染它
  const h1 = useMemo(() => paragraphs.find((p) => p.style === "Heading 1") ?? null, [paragraphs]);
  const docTitle = h1?.text ?? doc?.filename.replace(/\.(docx|txt)$/i, "") ?? "";
  const body = useMemo(
    () => (h1 ? paragraphs.filter((p) => p.para_no !== h1.para_no) : paragraphs),
    [paragraphs, h1],
  );
  const candidates = useMemo(
    () => (selected == null ? [] : requirements.filter((r) => r.para === selected)),
    [selected, requirements],
  );

  // 默认选中第一条需求对应的段落；没有就退到正文第一段
  useEffect(() => {
    if (selected != null || paragraphs.length === 0) return;
    const preferred = requirements.find((r) => r.para > 0)?.para ?? null;
    const hit =
      paragraphs.find((p) => p.para_no === preferred) ??
      paragraphs.find((p) => !p.is_heading) ??
      paragraphs[0];
    setSelected(hit.para_no);
  }, [paragraphs, selected, requirements]);

  // 选中段落滚动到视野中央
  useEffect(() => {
    if (selected == null) return;
    const pane = paperRef.current;
    const el = pane?.querySelector<HTMLElement>(`[data-para="${selected}"]`);
    if (!pane || !el) return;
    const top = el.getBoundingClientRect().top - pane.getBoundingClientRect().top + pane.scrollTop;
    pane.scrollTop = Math.max(0, top - pane.clientHeight / 2 + el.offsetHeight / 2);
  }, [selected]);

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">STEP 02 · 文档</div>
          <h1 className="page-title">文档工作台</h1>
          <div className="page-sub">
            {doc
              ? `${doc.filename} · ${doc.version} · ${doc.paragraphs} 段 · 解析完成`
              : "上传一份需求文档，平台会解析段落并保留原文位置。"}
          </div>
        </div>
        <div className="head-actions">
          <button className="btn" type="button" onClick={() => setUploadOpen((v) => !v)}>
            <Icon name="upload" />
            上传文档
          </button>
          <button
            className="btn primary"
            type="button"
            disabled={!doc || extracting || !!apiError}
            title={doc ? "调用大模型从文档重新抽取需求" : "先上传一份文档"}
            style={!doc || apiError ? { opacity: 0.55, cursor: "not-allowed" } : undefined}
            onClick={() => {
              if (!doc) return;
              if (requirements.length > 0) {
                setExtractOpen(true);
                setExtractMsg(null);
              } else {
                void runExtract();
              }
            }}
          >
            <Icon name="flask" />
            {extracting ? `抽取中 ${elapsed}s` : "抽取需求"}
          </button>
        </div>
      </div>

      {uploadOpen ? <UploadCard onClose={() => setUploadOpen(false)} /> : null}

      {extractOpen ? (
        <div className="card extract-card">
          <div className="card-h">
            <span className="t">重新抽取需求</span>
            <span className="m">会覆盖当前 {requirements.length} 条</span>
          </div>
          <div className="card-b extract-body">
            <div className="extract-note">
              将调用大模型重新解析整份文档，并清空当前项目的 {requirements.length} 条需求（含已确认的）。
              预计 10–30 秒，期间不要关闭页面。
            </div>
            <button
              className="btn ghost"
              type="button"
              disabled={extracting}
              onClick={() => setExtractOpen(false)}
            >
              取消
            </button>
            <button className="btn primary" type="button" disabled={extracting} onClick={runExtract}>
              {extracting ? `抽取中… ${elapsed}s` : "覆盖并抽取"}
            </button>
          </div>
        </div>
      ) : null}

      {extracting && !extractOpen ? (
        <div className="extract-status">正在调用大模型抽取… 已等待 {elapsed}s</div>
      ) : null}

      {extractMsg ? (
        <div className={`extract-status ${extractMsg.kind}`}>
          {extractMsg.text}
          {extractMsg.kind === "ok" ? (
            <Link href="/requirements" style={{ marginLeft: 10, textDecoration: "underline" }}>
              去核对
            </Link>
          ) : null}
        </div>
      ) : null}

      {apiError ? (
        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name="alert" size={20} />
            </div>
            <h3>后端没有连上</h3>
            <p>
              先启动 FastAPI（端口 8000），再刷新本页。当前错误：<code>{apiError}</code>
            </p>
            <code className="codeblock">
              .\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000
            </code>
            <div className="row">
              <a className="btn" href="/document">
                重试
              </a>
            </div>
          </div>
        </div>
      ) : !doc ? (
        <div className="card">
          <div className="empty">
            <div className="ic">
              <Icon name="doc" size={20} />
            </div>
            <h3>还没有上传文档</h3>
            <p>上传 DOCX 或 TXT，解析结果会存进 App/data/ratgp.db，原始文件保留在 App/data/uploads。</p>
            <div className="row">
              <button className="btn primary" type="button" onClick={() => setUploadOpen(true)}>
                上传文档
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="doc-grid"
          style={{
            height: uploadOpen ? "calc(100vh - 372px)" : extractOpen ? "calc(100vh - 330px)" : undefined,
          }}
        >
          <div className="card pane">
            <div className="pane-h">
              <Icon name="quote" size={13} />
              段落大纲
              <span style={{ marginLeft: "auto" }}>{headings.length}</span>
            </div>
            <div className="pane-b">
              {headings.map((h) => (
                <div
                  key={h.para_no}
                  className={`outline-item h${h.para_no === selected ? " active" : ""}`}
                  onClick={() => setSelected(h.para_no)}
                >
                  <span className="no">{h.para_no}</span>
                  <span>{h.text}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card pane">
            <div className="pane-h">
              <span style={{ color: "var(--text-2)" }}>{doc.filename}</span>
              <span className="chip" style={{ marginLeft: "auto" }}>
                {doc.version}
              </span>
              <span className="chip ok">
                <span className="dot" />
                已解析
              </span>
            </div>
            <div className="pane-b paper" ref={paperRef}>
              <div className="paper-inner">
                <div className="doc-title">{docTitle}</div>
                <div className="doc-meta">
                  {doc.filename} · {doc.version} · {doc.paragraphs} 段 · 解析于 {formatApiTime(doc.upload_time)}
                </div>
                {body.map((p) => (
                  <div
                    key={p.para_no}
                    data-para={p.para_no}
                    className={`p${p.is_heading ? " hd" : ""}${p.para_no === selected ? " active" : ""}`}
                    onClick={() => setSelected(p.para_no)}
                  >
                    <div className="no">{p.para_no}</div>
                    <div className="tx">{p.text}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card pane">
            <div className="pane-h">
              <Icon name="flask" size={13} />
              候选需求
              <span style={{ marginLeft: "auto" }}>{candidates.length || "—"}</span>
            </div>
            <div className="cand">
              {candidates.length > 0 ? (
                candidates.map((c) => (
                  <div className="cand-card" key={c.id}>
                    <div className="ch">
                      <span className="id">{c.id}</span>
                      <span className="chip accent">候选</span>
                      <span className="chip" style={{ marginLeft: "auto" }}>
                        {c.type === "functional" ? "功能" : "非功能"}
                      </span>
                    </div>
                    <div className="ti">{c.title}</div>
                    <div className="de">{c.desc}</div>
                    <ul className="ac">
                      {c.acc.slice(0, 3).map((a, i) => (
                        <li key={i}>
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                    <div style={{ marginTop: 9, display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {c.risks.map((k) => (
                        <span key={k} className={`chip ${k === "ambiguous" ? "warn" : "danger"}`}>
                          {k === "ambiguous" ? "模糊" : "冲突"}
                        </span>
                      ))}
                      <span className="chip">¶{c.para}</span>
                    </div>
                    <div className="ft">
                      <Link className="btn sm" href={`/requirements?open=${c.id}`}>
                        查看需求
                      </Link>
                    </div>
                  </div>
                ))
              ) : (
                <div className="cand-empty">
                  <Icon name="flask" size={16} />
                  <div>这一段还没有候选需求</div>
                  <div className="hint">P3 会调用 LLM 从全文抽取，结果按段落挂到右侧。</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
