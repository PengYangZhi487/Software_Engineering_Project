import type { Metadata } from "next";
import { Offline } from "@/components/offline";
import { SearchView } from "@/components/search-view";
import { Icon } from "@/components/icon";
import { loadSearch } from "@/lib/server";

export const metadata: Metadata = { title: "搜索 · RATGP" };

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const keyword = (q ?? "").trim();

  if (!keyword) {
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
            <p>在顶部搜索框输入关键词后回车，或者直接访问 /search?q=容量。</p>
          </div>
        </div>
      </section>
    );
  }

  const feed = await loadSearch(1, keyword);
  if (feed.source === "mock") return <Offline message={feed.error} />;

  return <SearchView feed={feed} />;
}
