import AgentCard from "./AgentCard";
import BidFactsPanel from "./BidFactsPanel";
import CommitteeVoting from "./CommitteeVoting";
import DocumentInput from "./DocumentInput";
import ExecutiveReport from "./ExecutiveReport";
import MetricsBar from "./MetricsBar";
import WorkflowTimeline from "./WorkflowTimeline";

export default function ReviewView({ config, samples, run, busy, onRun, onError }) {
  return (
    <div className="space-y-4">
      <div className="print:hidden">
        <DocumentInput samples={samples} running={busy} onRun={onRun} onError={onError} />
      </div>

      {(busy || run.steps.length > 0) && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3 print:hidden">
          <WorkflowTimeline reached={run.steps} running={busy} />
          {run.log.length > 0 && (
            <p className="mt-2 font-mono text-[13px] text-slate-500">
              › {run.log[run.log.length - 1]}
            </p>
          )}
        </div>
      )}

      {run.committee && (
        <div className="flex justify-end print:hidden">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500"
          >
            📄 PDF 다운로드
          </button>
        </div>
      )}

      <BidFactsPanel facts={run.facts} />

      {config && (busy || Object.keys(run.opinions).length > 0) && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {config.agents.map((profile) => (
            <AgentCard
              key={profile.role}
              profile={profile}
              opinion={run.opinions[profile.role]}
              status={run.running[profile.role] ? "running" : "idle"}
            />
          ))}
        </div>
      )}

      <CommitteeVoting committee={run.committee} />
      <ExecutiveReport committee={run.committee} />
      <div className="print:hidden">
        <MetricsBar metrics={run.metrics} />
      </div>
    </div>
  );
}
