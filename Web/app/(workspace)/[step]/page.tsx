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
  cases: {
    eyebrow: "STEP 05 · 用例",
    title: "测试用例",
    sub: "正常 / 异常 / 边界三类，schema 校验通过后进入人工审核。",
    icon: "flask",
    emptyTitle: "用例工作台在 P5 接入",
    emptyBody:
      "P5 会补上 case_service：按已确认需求生成三类候选用例，LLM 只提候选，Pydantic 校验字段、程序校验引用的需求是否存在。",
    primary: { href: "/trace", label: "看追踪矩阵" },
  },
  trace: {
    eyebrow: "STEP 06 · 追踪",
    title: "追踪矩阵",
    sub: "需求 × 测试用例。未覆盖的需求就是下一轮测试要补的洞。",
    icon: "grid",
    emptyTitle: "追踪矩阵在 P6 接入",
    emptyBody:
      "P6 会把需求与用例的多对多关联、覆盖率计算和未覆盖清单做进来；覆盖率必须能由 SQL 独立复算，页面只是它的展示。",
    primary: { href: "/requirements", label: "回到需求库" },
  },
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
