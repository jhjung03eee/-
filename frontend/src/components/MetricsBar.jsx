import { percent } from "../lib/format";

function Metric({ label, value, hint }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2">
      <p className="text-xs tracking-wide text-slate-500 uppercase">{label}</p>
      <p className="font-mono text-base font-semibold text-slate-200">{value}</p>
      {hint && <p className="text-xs text-slate-600">{hint}</p>}
    </div>
  );
}

export default function MetricsBar({ metrics }) {
  if (!metrics) return null;
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      <Metric label="Latency" value={`${metrics.total_latency_ms} ms`} />
      <Metric label="Chunks" value={metrics.chunk_count} />
      <Metric
        label="Citation Validity"
        value={percent(metrics.citation_validity_rate)}
        hint={`${metrics.valid_citation_count}/${metrics.citation_count}`}
      />
      <Metric label="Grounding" value={percent(metrics.grounding_rate)} />
      <Metric label="Mean Confidence" value={percent(metrics.mean_confidence)} />
      <Metric label="Provider" value={metrics.llm_provider} />
    </div>
  );
}
