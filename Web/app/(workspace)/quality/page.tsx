import { QualityBoard } from "@/components/quality-board";
import { loadQuality } from "@/lib/server";

export const metadata = { title: "质量分析 · RATGP" };

export default async function QualityPage() {
  const feed = await loadQuality(1);
  return <QualityBoard feed={feed} />;
}
