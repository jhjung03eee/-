const STAGES = [
  { key: "parsing", label: "공고 파싱" },
  { key: "indexing", label: "RAG 인덱싱" },
  { key: "agents", label: "위원 검토" },
  { key: "committee", label: "위원회 의결" },
  { key: "validation", label: "가드레일 검증" },
  { key: "completed", label: "보고서 생성" },
];

export default function WorkflowTimeline({ reached, running }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 text-sm">
      {STAGES.map((stage, index) => {
        const done = reached.includes(stage.key);
        const active = running && !done && reached.includes(STAGES[index - 1]?.key);
        return (
          <li key={stage.key} className="flex items-center gap-2">
            <span
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors ${
                done
                  ? "border-sky-500/40 bg-sky-500/10 text-sky-300"
                  : active
                    ? "pulse-ring border-sky-500/40 bg-slate-800 text-slate-200"
                    : "border-slate-800 bg-slate-900 text-slate-600"
              }`}
            >
              <span className="font-mono">{done ? "✓" : index + 1}</span>
              {stage.label}
            </span>
            {index < STAGES.length - 1 && <span className="text-slate-700">→</span>}
          </li>
        );
      })}
    </ol>
  );
}
