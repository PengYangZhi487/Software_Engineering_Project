import { Offline } from "@/components/offline";
import { TraceBoard } from "@/components/trace-board";
import { loadTrace } from "@/lib/server";

export const metadata = { title: "追踪矩阵 · RATGP" };

export default async function TracePage() {
  const feed = await loadTrace(1);
  if (feed.source === "mock") return <Offline message={feed.error} />;
  return <TraceBoard feed={feed} />;
}
