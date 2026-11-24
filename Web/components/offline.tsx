"use client";

import { notifyDataChanged } from "@/lib/use-api";
import { Icon } from "./icon";

/**
 * 后端连不上时统一渲染的离线页。
 *
 * 之前各页面各自处理：总览和需求会回退 mock 假数据，报告直接报错，
 * 追踪显示空矩阵——口径对不上。现在全部走这一个组件。
 */
export function Offline({
  message,
  title = "后端没有连上",
}: {
  message?: string | null;
  title?: string;
}) {
  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">OFFLINE</div>
          <h1 className="page-title">{title}</h1>
          <div className="page-sub">前端已启动，但没有连上 FastAPI（8000）。</div>
        </div>
      </div>

      <div className="card">
        <div className="empty">
          <div className="ic">
            <Icon name="alert" size={20} />
          </div>
          <h3>读不到数据</h3>
          <p>{message || "先启动后端，再点「重试」。"}</p>
          <code className="codeblock">
            .\venv\Scripts\python.exe -m uvicorn App.api.main:app --reload --port 8000
          </code>
          <div className="row">
            <button className="btn primary" type="button" onClick={() => notifyDataChanged()}>
              重试
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
