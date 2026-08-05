import { useState } from "react";
import { decisionStyle, krw, percent } from "../lib/format";
import useFillWidth from "../lib/useFillWidth";
import Panel from "./Panel";

const TIER = {
  적극추천: {
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    accent: "border-l-emerald-500",
    bar: "bg-emerald-500",
    icon: "🚀",
  },
  검토: {
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/40",
    accent: "border-l-amber-500",
    bar: "bg-amber-500",
    icon: "👀",
  },
  패스: {
    text: "text-slate-500",
    bg: "bg-slate-700/20",
    border: "border-slate-700",
    accent: "border-l-slate-700",
    bar: "bg-slate-600",
    icon: "🚫",
  },
};

const tierStyle = (tier) => TIER[tier] || TIER["검토"];

function DistributionBar({ report }) {
  const total = report.total || 1;
  const segments = [
    { tier: "적극추천", count: report.counts["적극추천"] || 0 },
    { tier: "검토", count: report.counts["검토"] || 0 },
    { tier: "패스", count: report.counts["패스"] || 0 },
  ];
  return (
    <div className="mb-4">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-800">
        {segments.map((seg) => {
          const width = useFillWidth((seg.count / total) * 100);
          return seg.count > 0 ? (
            <div
              key={seg.tier}
              className={`h-full ${tierStyle(seg.tier).bar} transition-[width] duration-700 ease-out first:rounded-l-full last:rounded-r-full`}
              style={{ width: `${width}%` }}
              title={`${seg.tier} ${seg.count}건`}
            />
          ) : null;
        })}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-slate-500">
        {segments.map((seg) => (
          <span key={seg.tier} className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${tierStyle(seg.tier).bar}`} />
            {tierStyle(seg.tier).icon} {seg.tier} {seg.count}건 (
            {Math.round((seg.count / total) * 100)}%)
          </span>
        ))}
      </div>
    </div>
  );
}

function Summary({ report }) {
  const tiles = [
    { label: "전체 공고", value: report.total, icon: "📋" },
    { label: "적극추천", value: report.counts["적극추천"], tone: "text-emerald-400", icon: "🚀" },
    { label: "검토", value: report.counts["검토"], tone: "text-amber-400", icon: "👀" },
    { label: "패스", value: report.counts["패스"], tone: "text-slate-400", icon: "🚫" },
    { label: "사전 필터링", value: report.filtered_out, hint: "위원회 미실행", icon: "🧹" },
    {
      label: "소요 시간",
      value:
        report.total_latency_ms < 1000
          ? `${report.total_latency_ms}ms`
          : `${(report.total_latency_ms / 1000).toFixed(1)}s`,
      icon: "⏱️",
    },
  ];
  return (
    <>
      <DistributionBar report={report} />
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {tiles.map((tile) => (
          <div
            key={tile.label}
            className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 transition-colors hover:border-slate-700"
          >
            <p className="flex items-center gap-1.5 text-[13px] tracking-wide text-slate-500 uppercase">
              <span aria-hidden>{tile.icon}</span>
              {tile.label}
            </p>
            <p className={`font-mono text-lg font-bold ${tile.tone || "text-slate-200"}`}>
              {tile.value}
            </p>
            {tile.hint && <p className="text-[13px] text-slate-600">{tile.hint}</p>}
          </div>
        ))}
      </div>
    </>
  );
}

function Detail({ item }) {
  if (item.screen.blocked) {
    return (
      <div className="space-y-1 bg-slate-950/60 px-4 py-3">
        <p className="text-sm text-slate-400">
          사전 필터에서 제외되어 위원회 심의를 실행하지 않았습니다.
        </p>
        {item.screen.block_reasons.map((reason, i) => (
          <p key={i} className="text-sm text-rose-300">
            · {reason}
          </p>
        ))}
      </div>
    );
  }

  if (!item.committee) {
    return (
      <div className="bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
        {item.error || "심의 결과가 없습니다."}
      </div>
    );
  }

  return (
    <div className="space-y-3 bg-slate-950/60 px-4 py-3">
      <div className="flex flex-wrap gap-2">
        {item.committee.votes.map((vote) => {
          const style = decisionStyle(vote.decision);
          return (
            <span
              key={vote.role}
              className={`rounded-md border px-2 py-1 text-[14px] ${style.border} ${style.bg}`}
            >
              <span className="text-slate-400">{vote.display_name}</span>{" "}
              <span className={`font-bold ${style.text}`}>{vote.decision}</span>{" "}
              <span className="font-mono text-slate-500">{percent(vote.confidence)}</span>
            </span>
          );
        })}
      </div>

      <p className="text-sm leading-relaxed text-slate-300">
        {item.committee.executive_summary}
      </p>

      <div className="grid gap-3 md:grid-cols-2">
        {item.committee.key_strengths?.length > 0 && (
          <ul className="space-y-0.5">
            {item.committee.key_strengths.slice(0, 3).map((text, i) => (
              <li key={i} className="text-[14px] text-emerald-300/90">
                + {text}
              </li>
            ))}
          </ul>
        )}
        {item.committee.key_risks?.length > 0 && (
          <ul className="space-y-0.5">
            {item.committee.key_risks.slice(0, 3).map((text, i) => (
              <li key={i} className="text-[14px] text-rose-300/90">
                ! {text}
              </li>
            ))}
          </ul>
        )}
      </div>

      {item.screen.warnings?.length > 0 && (
        <p className="text-[14px] text-amber-300">
          {item.screen.warnings.join(" · ")}
        </p>
      )}
    </div>
  );
}

function Row({ item, expanded, onToggle, index }) {
  const style = tierStyle(item.recommendation);
  return (
    <>
      <tr
        onClick={onToggle}
        className="fade-in-up cursor-pointer border-t border-slate-800 hover:bg-slate-800/30"
        style={{ animationDelay: `${Math.min(index, 12) * 40}ms` }}
      >
        <td className={`border-l-4 py-2.5 pr-3 pl-2.5 ${style.accent}`}>
          <span
            className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[14px] font-bold ${style.bg} ${style.text}`}
          >
            <span aria-hidden>{style.icon}</span>
            {item.recommendation}
          </span>
        </td>
        <td className="px-3 py-2.5">
          <p className="truncate text-sm font-medium text-slate-200">{item.title}</p>
          <p className="truncate text-[14px] text-slate-500">
            {item.bid_id} · {item.agency || "발주처 미확인"}
          </p>
        </td>
        <td className="px-3 py-2.5 text-right font-mono text-sm text-slate-300">
          {krw(item.budget_krw)}
        </td>
        <td className="px-3 py-2.5 text-right">
          {item.days_left === null ? (
            <span className="text-[14px] text-slate-600">미확인</span>
          ) : (
            <span
              className={`font-mono text-sm ${
                item.days_left < 0
                  ? "text-slate-600"
                  : item.urgent
                    ? "font-bold text-rose-400"
                    : "text-slate-300"
              }`}
            >
              D{item.days_left >= 0 ? "-" : "+"}
              {Math.abs(item.days_left)}
            </span>
          )}
        </td>
        <td className="px-3 py-2.5 text-right font-mono text-sm text-slate-400">
          {item.score.toFixed(2)}
        </td>
        <td className="max-w-md px-3 py-2.5">
          <p className="truncate text-[14px] text-slate-400">{item.reason}</p>
        </td>
        <td className="px-3 py-2.5 text-center">
          {item.human_review_required && (
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[13px] text-amber-300">
              검토요
            </span>
          )}
        </td>
        <td className="px-2 py-2.5 text-slate-600 print:hidden">{expanded ? "−" : "+"}</td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={8} className="p-0">
            <Detail item={item} />
          </td>
        </tr>
      )}
    </>
  );
}

export default function ScreeningView({ corpus, report, busy, onRun }) {
  const [expanded, setExpanded] = useState(null);

  return (
    <div className="space-y-4">
      <div className="print:hidden">
        <Panel
          title="배치 스크리닝"
          subtitle={
            corpus?.available
              ? `${corpus.count}건 공고 · ${corpus.path}`
              : "공고 코퍼스를 찾을 수 없습니다"
          }
          actions={
            <button
              onClick={onRun}
              disabled={busy || !corpus?.available}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
            >
              {busy ? "스크리닝 중…" : "일괄 스크리닝 실행"}
            </button>
          }
        >
          {!corpus?.available && (
            <p className="text-sm text-slate-400">
              <code className="text-slate-300">projects/raw</code> 아래에{" "}
              <code className="text-slate-300">bids_md/</code>,{" "}
              <code className="text-slate-300">bid_meta/</code> 를 배치하거나{" "}
              <code className="text-slate-300">BIDCOM_CORPUS_DIR</code> 환경변수로 경로를
              지정하세요.
            </p>
          )}
          {corpus?.available && !report && !busy && (
            <p className="text-sm text-slate-400">
              사전 필터(자격미달 · 예산미달 · 마감경과)를 먼저 적용하고, 통과한 공고에 대해서만
              4개 위원 심의를 실행합니다.
            </p>
          )}
          {busy && (
            <p className="text-sm text-sky-400">
              공고를 파싱하고 위원회 심의를 실행하는 중입니다…
            </p>
          )}
        </Panel>
      </div>

      {report && (
        <Panel
          title="스크리닝 리포트"
          subtitle="적극추천 → 검토 → 패스 순, 동일 등급 내에서는 마감 임박 순"
          actions={
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-500">
                {report.company} · {report.generated_at}
              </span>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-2 rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 print:hidden"
              >
                📄 PDF 다운로드
              </button>
            </div>
          }
        >
          <div className="mb-4">
            <Summary report={report} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px]">
              <thead>
                <tr className="text-sm tracking-wide text-slate-500 uppercase">
                  <th className="px-3 pb-2 text-left">등급</th>
                  <th className="px-3 pb-2 text-left">공고</th>
                  <th className="px-3 pb-2 text-right">예산</th>
                  <th className="px-3 pb-2 text-right">마감</th>
                  <th className="px-3 pb-2 text-right">점수</th>
                  <th className="px-3 pb-2 text-left">판단 근거</th>
                  <th className="px-3 pb-2" />
                  <th className="px-2 pb-2 print:hidden" />
                </tr>
              </thead>
              <tbody>
                {report.items.map((item, index) => (
                  <Row
                    key={item.bid_id}
                    item={item}
                    index={index}
                    expanded={expanded === item.bid_id}
                    onToggle={() =>
                      setExpanded((prev) => (prev === item.bid_id ? null : item.bid_id))
                    }
                  />
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
