import { decisionStyle, percent, score10 } from "../lib/format";
import useFillWidth from "../lib/useFillWidth";
import CommitteeAvatar from "./CommitteeAvatar";
import Panel from "./Panel";

function VoteBar({ pct, tone }) {
  const width = useFillWidth(pct);
  return (
    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-800">
      <div
        className={`h-full rounded-full ${tone} transition-[width] duration-700 ease-out`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export default function CommitteeVoting({ committee }) {
  if (!committee) return null;
  const maxWeight = Math.max(...committee.votes.map((v) => v.weight), 0.001);

  return (
    <Panel
      title="위원회 가중 투표"
      subtitle="가중치 × 신뢰도로 표의 영향력을 조정한다"
      actions={
        <span className="font-mono text-sm text-slate-400">
          스코어 {score10(committee.committee_score)}
        </span>
      }
    >
      <div className="space-y-3">
        {committee.votes.map((vote, i) => {
          const style = decisionStyle(vote.decision);
          return (
            <div
              key={vote.role}
              className="fade-in-up flex items-center gap-3"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <CommitteeAvatar role={vote.role} size={28} />
              <span className="w-24 shrink-0 truncate text-sm text-slate-300">
                {vote.display_name}
              </span>
              <span className={`w-16 shrink-0 text-sm font-bold ${style.text}`}>
                {vote.decision}
              </span>
              <VoteBar pct={(vote.weight / maxWeight) * 100} tone={style.dot} />
              <span className="w-28 shrink-0 text-right font-mono text-[14px] text-slate-400">
                w{vote.weight.toFixed(2)} · {percent(vote.confidence)}
              </span>
            </div>
          );
        })}
      </div>

      {committee.dissenting_roles?.length > 0 && (
        <p className="mt-4 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[14px] text-amber-300">
          소수의견 {committee.dissenting_roles.length}건 — 최종 판정과 다른 관점이 기록되었습니다.
        </p>
      )}
    </Panel>
  );
}
