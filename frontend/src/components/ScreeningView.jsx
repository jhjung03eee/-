import { useMemo, useState } from "react";
import { decisionStyle, krw, percent, score10 } from "../lib/format";
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
const TIER_ORDER = { 적극추천: 0, 검토: 1, 패스: 2 };
const ACTION_STATES = ["검토 전", "담당자 배정", "보류", "제외"];

const AS_OF_SOURCE_HINT = {
  corpus: "코퍼스의 마지막 공고일 기준",
  configured: "BIDCOM_AS_OF 설정값",
  today: "실행 시점",
  explicit: "호출 시 지정된 날짜",
};

/** D-day는 오늘이 아니라 이 기준일로부터 센 값이라, 화면에 함께 보여준다. */
function AsOfNote({ report }) {
  if (!report.as_of) return null;
  const hint = AS_OF_SOURCE_HINT[report.as_of_source] || report.as_of_source;
  return (
    <span
      className="rounded border border-slate-700 bg-slate-900/70 px-2 py-0.5 font-mono text-xs text-slate-400"
      title={`마감일 판정 기준일 — ${hint}`}
    >
      기준일 {report.as_of}
      <span className="ml-1.5 text-slate-600">{hint}</span>
    </span>
  );
}

function deadlineLabel(item) {
  if (item.days_left === null) return "마감 미확인";
  return `D${item.days_left >= 0 ? "-" : "+"}${Math.abs(item.days_left)}`;
}

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

function PrintReport({ report }) {
  const sorted = [...report.items].sort(
    (a, b) =>
      TIER_ORDER[a.recommendation] - TIER_ORDER[b.recommendation] ||
      (a.days_left ?? Infinity) - (b.days_left ?? Infinity) ||
      b.score - a.score
  );
  const reasonFor = (item) => {
    if (item.screen.blocked) {
      return item.screen.block_reasons?.join(" · ") || "사전 필터 제외";
    }
    const text = item.committee?.executive_summary || item.error || "-";
    return text.length > 90 ? `${text.slice(0, 90)}…` : text;
  };
  return (
    <table className="hidden w-full border-collapse text-left print:table">
      <thead>
        <tr className="border-b border-slate-400 text-slate-600">
          <th className="py-1 pr-1 font-semibold">등급</th>
          <th className="py-1 pr-1 font-semibold">공고명</th>
          <th className="py-1 pr-1 font-semibold">발주처</th>
          <th className="py-1 pr-1 text-right font-semibold">예산</th>
          <th className="py-1 pr-1 text-right font-semibold">마감</th>
          <th className="py-1 pr-1 font-semibold">요약 / 사유</th>
          <th className="py-1 text-right font-semibold">점수</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((item) => (
          <tr key={item.bid_id} className="border-b border-slate-200 align-top">
            <td className="py-1 pr-1 font-semibold">
              {tierStyle(item.recommendation).icon} {item.recommendation}
            </td>
            <td className="py-1 pr-1">{item.title}</td>
            <td className="py-1 pr-1">{item.agency || "-"}</td>
            <td className="py-1 pr-1 text-right font-mono">{krw(item.budget_krw)}</td>
            <td className="py-1 pr-1 text-right font-mono">{deadlineLabel(item)}</td>
            <td className="py-1 pr-1">{reasonFor(item)}</td>
            <td className="py-1 text-right font-mono">{score10(item.score)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ActionSelect({ value, onChange }) {
  return (
    <select
      value={value}
      onChange={onChange}
      onClick={(event) => event.stopPropagation()}
      className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 outline-none focus:border-sky-500"
      aria-label="업무 상태"
    >
      {ACTION_STATES.map((status) => (
        <option key={status}>{status}</option>
      ))}
    </select>
  );
}

function QueueCard({ item, onSelect, selected }) {
  const style = tierStyle(item.recommendation);
  return (
    <button
      onClick={() => onSelect(item.bid_id)}
      className={`fade-in-up min-w-0 rounded-lg border border-l-4 p-3 text-left transition ${style.accent} ${
        selected
          ? "border-sky-400 bg-slate-800/80 shadow-[0_8px_20px_rgb(0_0_0_/_0.18)]"
          : "border-slate-800 bg-slate-900/55 hover:border-slate-700 hover:bg-slate-800/60"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${style.bg} ${style.text}`}>
          {style.icon} {item.recommendation}
        </span>
        <span className={`font-mono text-sm font-bold ${style.text}`}>{score10(item.score)}</span>
      </div>
      <p className="mt-2 line-clamp-2 text-sm font-semibold leading-snug text-slate-100">{item.title}</p>
      <p className="mt-1 truncate text-xs text-slate-500">{item.agency || "발주처 미확인"}</p>
      <div className="mt-3 flex items-center justify-between gap-2 text-xs">
        <span className="font-mono text-slate-400">{krw(item.budget_krw)}</span>
        <span className={item.urgent ? "font-mono font-bold text-rose-400" : "font-mono text-slate-400"}>
          {deadlineLabel(item)}
        </span>
      </div>
    </button>
  );
}

function ListItem({ item, selected, status, onSelect, onStatusChange }) {
  const style = tierStyle(item.recommendation);
  return (
    <div
      className={`flex w-full items-center gap-3 border-l-4 px-3 py-3 text-left transition ${style.accent} ${
        selected ? "bg-sky-500/10" : "hover:bg-slate-800/55"
      }`}
    >
      <button onClick={() => onSelect(item.bid_id)} className="flex min-w-0 flex-1 items-center gap-3 text-left" aria-label={`${item.title} 상세 보기`}>
        <span className={`hidden shrink-0 rounded px-1.5 py-0.5 text-xs font-bold sm:inline ${style.bg} ${style.text}`}>
          {style.icon} {item.recommendation}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <p className="truncate text-sm font-medium text-slate-100">{item.title}</p>
            {item.human_review_required && <span className="shrink-0 text-xs" title="담당자 검토 필요">⚠️</span>}
          </div>
          <p className="mt-0.5 truncate text-xs text-slate-500">
            {item.category && <span className="mr-1.5 rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">{item.category}</span>}
            {item.agency || "발주처 미확인"}
          </p>
        </div>
        <div className="hidden w-20 shrink-0 text-right sm:block">
          <p className={`font-mono text-sm font-bold ${style.text}`}>{score10(item.score)}</p>
          <p className={item.urgent ? "font-mono text-xs font-bold text-rose-400" : "font-mono text-xs text-slate-500"}>{deadlineLabel(item)}</p>
        </div>
      </button>
      <ActionSelect value={status} onChange={(event) => onStatusChange(item.bid_id, event.target.value)} />
    </div>
  );
}

function DetailPanel({ item, status, onStatusChange }) {
  if (!item) {
    return <div className="flex min-h-72 items-center justify-center border border-dashed border-slate-800 px-5 text-center text-sm text-slate-500">목록에서 공고를 선택하면 심의 근거와 위원회 의견을 확인할 수 있습니다.</div>;
  }
  const style = tierStyle(item.recommendation);
  return (
    <aside className="border border-slate-800 bg-slate-900/55 xl:sticky xl:top-4">
      <div className={`border-l-4 p-4 ${style.accent}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${style.bg} ${style.text}`}>{style.icon} {item.recommendation}</span>
            <h3 className="mt-2 text-base font-semibold leading-snug text-slate-50">{item.title}</h3>
            <p className="mt-1 text-xs text-slate-500">
              {item.category && <span className="mr-1.5 rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">{item.category}</span>}
              {item.bid_id} · {item.agency || "발주처 미확인"}
            </p>
          </div>
          <span className={`font-mono text-lg font-bold ${style.text}`}>{score10(item.score)}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 border-y border-slate-800 py-3 text-xs">
          <div><p className="text-slate-500">예산</p><p className="mt-0.5 font-mono text-slate-200">{krw(item.budget_krw)}</p></div>
          <div><p className="text-slate-500">마감</p><p className={`mt-0.5 font-mono ${item.urgent ? "font-bold text-rose-400" : "text-slate-200"}`}>{deadlineLabel(item)}</p></div>
          <div><p className="text-slate-500">업무 상태</p><div className="mt-1"><ActionSelect value={status} onChange={(event) => onStatusChange(item.bid_id, event.target.value)} /></div></div>
        </div>
      </div>
      <Detail item={item} />
    </aside>
  );
}

export default function ScreeningView({ corpus, report, busy, onRun }) {
  const [selectedId, setSelectedId] = useState(null);
  const [tierFilter, setTierFilter] = useState("전체");
  const [sortBy, setSortBy] = useState("priority");
  const [actionStatus, setActionStatus] = useState({});

  const updateStatus = (bidId, status) => setActionStatus((current) => ({ ...current, [bidId]: status }));
  const selectedItem = report?.items.find((item) => item.bid_id === selectedId) || null;
  const visibleItems = useMemo(() => {
    if (!report) return [];
    return report.items
      .filter((item) => tierFilter === "전체" || item.recommendation === tierFilter)
      .sort((a, b) => {
        if (sortBy === "score") return b.score - a.score;
        if (sortBy === "deadline") return (a.days_left ?? Infinity) - (b.days_left ?? Infinity);
        return (
          TIER_ORDER[a.recommendation] - TIER_ORDER[b.recommendation] ||
          (a.days_left ?? Infinity) - (b.days_left ?? Infinity) ||
          b.score - a.score
        );
      });
  }, [report, sortBy, tierFilter]);
  const priorityItems = useMemo(() => {
    if (!report) return [];
    return [...report.items]
      .filter((item) => !item.screen.blocked && item.recommendation !== "패스")
      .sort(
        (a, b) =>
          TIER_ORDER[a.recommendation] - TIER_ORDER[b.recommendation] ||
          (a.days_left ?? Infinity) - (b.days_left ?? Infinity) ||
          b.score - a.score
      )
      .slice(0, 3);
  }, [report]);

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
        <div className="space-y-4">
          <Panel title="스크리닝 개요" subtitle={`${report.company} · ${report.generated_at}`} actions={<div className="flex items-center gap-2"><AsOfNote report={report} /><button onClick={() => window.print()} className="flex items-center gap-2 rounded-md bg-sky-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 print:hidden">📄 PDF 다운로드</button></div>}>
            <Summary report={report} />
          </Panel>

          <section className="print:hidden">
            <div className="mb-2 flex items-center justify-between"><div><h2 className="text-base font-semibold text-slate-100">오늘의 우선 검토</h2><p className="mt-0.5 text-sm text-slate-500">점수와 등급 기준으로 먼저 확인할 공고입니다.</p></div><span className="font-mono text-sm text-slate-500">TOP {priorityItems.length}</span></div>
            <div className="grid gap-3 md:grid-cols-3">
              {priorityItems.map((item) => <QueueCard key={item.bid_id} item={item} selected={selectedId === item.bid_id} onSelect={setSelectedId} />)}
            </div>
          </section>

          <section className="grid gap-4 print:hidden xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.78fr)]">
            <div className="border border-slate-800 bg-slate-900/55">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 p-3">
                <div><h2 className="text-base font-semibold text-slate-100">전체 공고 목록</h2><p className="mt-0.5 text-xs text-slate-500">{visibleItems.length}건 표시 · 선택 시 오른쪽에서 상세 확인</p></div>
                <div className="flex flex-wrap items-center gap-2 print:hidden">
                  <select value={tierFilter} onChange={(event) => setTierFilter(event.target.value)} className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-300 outline-none focus:border-sky-500" aria-label="등급 필터">
                    <option>전체</option><option>적극추천</option><option>검토</option><option>패스</option>
                  </select>
                  <select value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-300 outline-none focus:border-sky-500" aria-label="정렬 기준">
                    <option value="priority">우선순위순</option><option value="score">점수순</option><option value="deadline">마감순</option>
                  </select>
                </div>
              </div>
              <div className="divide-y divide-slate-800">
                {visibleItems.map((item) => <ListItem key={item.bid_id} item={item} selected={selectedId === item.bid_id} status={actionStatus[item.bid_id] || "검토 전"} onSelect={setSelectedId} onStatusChange={updateStatus} />)}
              </div>
            </div>
            <DetailPanel item={selectedItem} status={selectedItem ? actionStatus[selectedItem.bid_id] || "검토 전" : "검토 전"} onStatusChange={updateStatus} />
          </section>

          <PrintReport report={report} />
        </div>
      )}
    </div>
  );
}
