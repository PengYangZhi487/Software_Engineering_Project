import Link from "next/link";
import { notFound } from "next/navigation";
import { Icon, type IconName } from "@/components/icon";

interface StepCopy {
  eyebrow: string;
  title: string;
  sub: string;
  icon: IconName;
  emptyTitle: string;
  emptyBody: string;
  primary?: { href: string; label: string };
  secondary?: string;
}

const STEPS: Record<string, StepCopy> = {
  changes: {
    eyebrow: "STEP 07 · 变更",
    title: "版本比对与影响",
    sub: "两版文档按需求条目对齐，差异落到条目级，再查受影响的用例。",
    icon: "diff",
    emptyTitle: "还没有第二个版本文档",
    emptyBody:
      "把容量从 50 改成 60、把退课窗口拉长到 4 周，都会让若干条需求与用例失效。P7 会上传 V1.1 并给出左右对照与影响清单。",
    secondary: "P7 接入",
  },
  report: {
    eyebrow: "STEP 08 · 报告",
    title: "质量报告",
    sub: "每个数字都能从数据库独立复算 —— 报告的价值在于可核对。",
    icon: "chart",
    emptyTitle: "报告模块在 P8 接入",
    emptyBody:
      "需求清单、问题列表、追踪矩阵、覆盖率、用例审核状态，一次导出 CSV / Excel，导出值与页面一致。",
    secondary: "P8 接入",
  },
};

export default async function StepPage({ params }: { params: Promise<{ step: string }> }) {
  const { step } = await params;
  const copy = STEPS[step];
  if (!copy) notFound();

  return (
    <section className="view active">
      <div className="view-head">
        <div>
          <div className="eyebrow">{copy.eyebrow}</div>
          <h1 className="page-title">{copy.title}</h1>
          <div className="page-sub">{copy.sub}</div>
        </div>
      </div>

      <div className="card">
        <div className="empty">
          <div className="ic">
            <Icon name={copy.icon} size={20} />
          </div>
          <h3>{copy.emptyTitle}</h3>
          <p>{copy.emptyBody}</p>
          <div className="row">
            {copy.primary ? (
              <Link className="btn" href={copy.primary.href}>
                {copy.primary.label}
              </Link>
            ) : null}
            {copy.secondary ? (
              <button className="btn ghost" type="button" title={copy.secondary}>
                {copy.secondary.length > 24 ? "看一个冲突示例" : copy.secondary}
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
