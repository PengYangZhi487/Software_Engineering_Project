import { ChangeBoard } from "@/components/change-board";
import { loadDiff } from "@/lib/server";

export const metadata = { title: "版本比对 · RATGP" };

export default async function ChangesPage() {
  const feed = await loadDiff(1);
  return <ChangeBoard feed={feed} />;
}
