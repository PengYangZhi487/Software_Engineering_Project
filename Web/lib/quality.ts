/**
 * 与后端 App/services/quality_service.py 保持同一套规则。
 * P1 在前端复刻一遍，P2 接入接口后由服务端返回，前端只负责展示。
 */
export const AMBIGUOUS_WORDS = [
  "快速", "高效", "及时", "尽快", "明显",
  "良好", "友好", "美观", "便捷", "稳定",
  "合理", "尽量", "适度", "充分", "适当",
  "无卡顿", "无延迟",
];

export function hitWords(text: string): string[] {
  return AMBIGUOUS_WORDS.filter((w) => text.includes(w));
}

/** 已经人工确认过的冲突组（真实数据集里故意埋的） */
export const CONFLICTS: Record<string, { with: string; note: string }> = {
  "CR-021": { with: "CR-006", note: "CR-006 规定每学期最多 6 门，本条要求 8 门，需产品方二选一。" },
  "CR-022": { with: "CR-007", note: "CR-007 规定第 2 周周五 18:00 后不可退课，本条允许 4 周内无条件退课。" },
  "CR-023": { with: "CR-008", note: "CR-008 规定默认容量 50 且管理员不得扩容，本条允许自动扩至 100。" },
  "CR-024": { with: "CR-009", note: "CR-009 规定成绩发布后不可修改，本条允许 7 天内任意修改。" },
  "CR-025": { with: "CR-008", note: "与 CR-008「不得扩容」、CR-023「扩容至 100」同时矛盾，属表述失控。" },
};
