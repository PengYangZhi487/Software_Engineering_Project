"use client";

/**
 * 站点根路径：静态导出没有服务端 redirect，改成挂载后客户端跳转。
 * （out/index.html 只负责把浏览器送进工作台）
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/overview");
  }, [router]);

  return (
    <div
      className="content"
      style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}
    >
      <section className="view active" style={{ width: "min(560px, 100%)" }}>
        <div className="card">
          <div className="empty">
            <div className="ic loading-pulse">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
                <path d="M4 7h16M4 12h11M4 17h14" />
              </svg>
            </div>
            <h3>正在进入工作台…</h3>
            <p>如果停在这里，点下面的按钮重试。</p>
            <div className="row">
              <button className="btn primary" type="button" onClick={() => router.replace("/overview")}>
                进入总览
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
