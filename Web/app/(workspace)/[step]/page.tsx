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

const STEPS: Record<string, StepCopy> = {};

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
