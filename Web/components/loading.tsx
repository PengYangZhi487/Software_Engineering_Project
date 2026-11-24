"use client";

import { Icon } from "./icon";

/**
 * 客户端取数的首屏骨架。
 * 静态导出后 HTML 里只有骨架，浏览器拿到数据才换成真实内容，所以每个页面统一用它。
 */
export function Loading({
  title = "正在读取数据…",
  hint = "正在从后端获取数据，首次启动可能要几秒。",
}: {
  title?: string;
  hint?: string;
}) {
  return (
    <section className="view active">
      <div className="card">
        <div className="empty">
          <div className="ic loading-pulse">
            <Icon name="flow" size={20} />
          </div>
          <h3>{title}</h3>
          <p>{hint}</p>
        </div>
      </div>
    </section>
  );
}
