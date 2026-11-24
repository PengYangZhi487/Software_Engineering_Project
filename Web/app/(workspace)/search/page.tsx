"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Icon } from "@/components/icon";
import { Loading } from "@/components/loading";
import { Offline } from "@/components/offline";
import { SearchView } from "@/components/search-view";
import { loadSearch } from "@/lib/data";
import { useCurrentProject } from "@/lib/project";
import { useApi } from "@/lib/use-api";

function EmptyState() {
  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">搜索</div>
          <h1 className="page-title">全局搜索</h1>
          <div className="page-sub">输入关键词，搜索需求编号 / 标题 / 描述、用例、质量问题。</div>
        </div>
      </div>
      <div className="card">
        <div className="empty">
          <div className="ic">
            <Icon name="search" size={20} />
          </div>
          <h3>从哪里开始</h3>
          <p>在顶部搜索框输入关键词后回车，或者直接访问 /search/?q=容量。</p>
        </div>
      </div>
    </section>
  );
}

function SearchPageInner() {
  const params = useSearchParams();
  const { projectId, ready } = useCurrentProject();
  const keyword = (params.get("q") ?? "").trim();

  const { data, loading, error } = useApi(
    () => (keyword ? loadSearch(projectId, keyword) : Promise.resolve(null)),
    [projectId, keyword],
  );

  if (!keyword) return <EmptyState />;
  if (!ready || loading || !data) return <Loading title="正在搜索…" hint={`正在查找「${keyword}」。`} />;
  if (error || data.source === "mock") return <Offline message={error ?? data.error} />;

  return <SearchView feed={data} />;
}

/** 静态导出下 useSearchParams 必须包一层 Suspense，否则构建时无法预渲染。 */
export default function SearchPage() {
  return (
    <Suspense fallback={<Loading title="正在搜索…" />}>
      <SearchPageInner />
    </Suspense>
  );
}
