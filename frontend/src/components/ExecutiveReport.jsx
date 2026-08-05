import { CHAIR_AVATAR, CHAIR_INITIAL, decisionStyle, percent, stars } from "../lib/format";
import Panel from "./Panel";

function List({ title, items, tone }) {
  if (!items?.length) return null;
  return (
    <div>
      <h4 className="mb-1.5 text-sm font-semibold tracking-wide text-slate-400 uppercase">
        {title}
      </h4>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className={`flex gap-2 text-sm leading-relaxed ${tone}`}>
            <span className="text-slate-600">—</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ExecutiveReport({ committee }) {
  if (!committee) return null;
  const style = decisionStyle(committee.decision);

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <span
            className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ring-2 ${CHAIR_AVATAR}`}
          >
            {CHAIR_INITIAL}
          </span>
          Executive Report
        </span>
      }
      subtitle="위원장 최종 판정 및 경영진 보고"
    >
      <div
        className={`mb-4 flex flex-wrap items-center gap-x-8 gap-y-3 rounded-lg border p-4 ${style.border} ${style.bg}`}
      >
        <div>
          <p className="text-sm text-slate-400">최종 판정</p>
          <p className={`text-4xl font-black tracking-tight ${style.text}`}>
            {committee.decision}
          </p>
        </div>
        <div>
          <p className="text-sm text-slate-400">위원회 신뢰도</p>
          <p className="font-mono text-3xl font-semibold text-slate-100">
            {percent(committee.confidence)}
          </p>
        </div>
        <div>
          <p className="text-sm text-slate-400">우선순위</p>
          <p className="text-3xl text-amber-400">{stars(committee.priority)}</p>
        </div>
        {committee.human_review_required && (
          <div className="ml-auto rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2">
            <p className="text-sm font-semibold text-amber-300">담당자 검토 필요</p>
            <ul className="mt-1 space-y-0.5">
              {committee.human_review_reasons.map((reason, i) => (
                <li key={i} className="text-[14px] text-amber-200/80">
                  · {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <p className="mb-4 text-base leading-relaxed text-slate-200">
        {committee.executive_summary}
      </p>

      <div className="grid gap-5 md:grid-cols-3">
        <List title="Strength" items={committee.key_strengths} tone="text-emerald-300/90" />
        <List title="Risk" items={committee.key_risks} tone="text-rose-300/90" />
        <List title="참여 조건" items={committee.conditions} tone="text-sky-300/90" />
      </div>
    </Panel>
  );
}
