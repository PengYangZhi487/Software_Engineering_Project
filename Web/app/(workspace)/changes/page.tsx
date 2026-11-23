import { ChangeBoard } from "@/components/change-board";
import { Offline } from "@/components/offline";
import { loadDiff } from "@/lib/server";

export const metadata = { title: "版本比对 · RATGP" };

export default async function ChangesPage() {
  const feed = await loadDiff(1);
  if (feed.source === "mock") return <Offline message={feed.message} />;
  return <ChangeBoard feed={feed} />;
}
