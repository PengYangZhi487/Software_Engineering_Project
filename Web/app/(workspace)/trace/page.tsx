import { TraceBoard } from "@/components/trace-board";
import { loadTrace } from "@/lib/server";

export const metadata = { title: "追踪矩阵 · RATGP" };

export default async function TracePage() {
  const feed = await loadTrace(1);
  return <TraceBoard feed={feed} />;
}
