import { krw } from "../lib/format";
import Panel from "./Panel";

function Field({ label, value }) {
  return (
    <div>
      <dt className="text-sm text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-base text-slate-200">{value || "미확인"}</dd>
    </div>
  );
}

export default function BidFactsPanel({ facts }) {
  if (!facts) return null;
  return (
    <Panel title="공고 정보" subtitle="에이전트 실행 전 구조화 추출">
      <dl className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <div className="col-span-2 md:col-span-3 lg:col-span-6">
          <Field label="사업명" value={facts.title} />
        </div>
        <Field label="발주기관" value={facts.agency} />
        <Field label="예산" value={facts.budget_krw ? krw(facts.budget_krw) : facts.budget_text} />
        <Field label="사업기간" value={facts.duration} />
        <Field label="지역" value={facts.region} />
        <Field label="마감" value={facts.deadline} />
        <Field label="자격요건" value={`${facts.qualifications?.length ?? 0}개 항목`} />
      </dl>
    </Panel>
  );
}
