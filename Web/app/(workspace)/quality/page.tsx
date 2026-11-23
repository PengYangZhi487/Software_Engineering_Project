import { Offline } from "@/components/offline";
import { QualityBoard } from "@/components/quality-board";
import { loadQuality } from "@/lib/server";

export const metadata = { title: "质量分析 · RATGP" };

export default async function QualityPage() {
  const feed = await loadQuality(1);
  if (feed.source === "mock") return <Offline message={feed.error} />;
  return <QualityBoard feed={feed} />;
}
