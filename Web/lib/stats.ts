import { cases, requirements } from "./data";

const ambiguous = requirements.filter((r) => r.risks.includes("ambiguous")).length;
const conflict = requirements.filter((r) => r.risks.includes("conflict")).length;
const confirmed = requirements.filter((r) => r.status === "confirmed").length;
const covered = requirements.filter((r) => r.covered).length;

export const stats = {
  total: requirements.length,
  confirmed,
  pending: requirements.length - confirmed,
  ambiguous,
  conflict,
  issues: ambiguous + conflict,
  cases: cases.length,
  covered,
  coveragePct: Math.round((covered / requirements.length) * 100),
};

export const byType = {
  functional: requirements.filter((r) => r.type === "functional").length,
  non_functional: requirements.filter((r) => r.type === "non_functional").length,
};
