import { useEffect, useRef, useState } from "react";
import ReviewView from "./components/ReviewView";
import ScreeningView from "./components/ScreeningView";
import { getConfig, getCorpus, getSamples, runScreening, streamReview } from "./lib/api";

const STAGE_TO_STEP = {
  parsing: "parsing",
  indexing: "indexing",
  agent_completed: "agents",
  committee_completed: "committee",
  validation: "validation",
  completed: "completed",
};

const initialRun = {
  facts: null,
  opinions: {},
  running: {},
  committee: null,
  metrics: null,
  steps: [],
  log: [],
};

const TABS = [
  { key: "screen", label: "배치 스크리닝" },
  { key: "review", label: "단건 심의" },
];

export default function App() {
  const [tab, setTab] = useState("screen");
  const [config, setConfig] = useState(null);
  const [samples, setSamples] = useState([]);
  const [corpus, setCorpus] = useState(null);
  const [report, setReport] = useState(null);
  const [run, setRun] = useState(initialRun);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef(null);

  useEffect(() => {
    Promise.all([getConfig(), getSamples(), getCorpus()])
      .then(([configData, sampleData, corpusData]) => {
        setConfig(configData);
        setSamples(sampleData.samples);
        setCorpus(corpusData);
      })
      .catch((err) => setError(err.message));
    return () => abortRef.current?.abort();
  }, []);

  const startScreening = async () => {
    setError("");
    setBusy(true);
    try {
      setReport(await runScreening());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleEvent = (event) => {
    setRun((prev) => {
      const next = {
        ...prev,
        log: [...prev.log, event.message].slice(-30),
        steps: STAGE_TO_STEP[event.stage]
          ? [...new Set([...prev.steps, STAGE_TO_STEP[event.stage]])]
          : prev.steps,
      };

      switch (event.stage) {
        case "parsing":
          next.facts = event.payload.facts;
          break;
        case "agent_started":
          next.running = { ...prev.running, [event.payload.role]: true };
          break;
        case "agent_completed": {
          const opinion = event.payload.opinion;
          next.opinions = { ...prev.opinions, [opinion.role]: opinion };
          next.running = { ...prev.running, [opinion.role]: false };
          break;
        }
        case "committee_completed":
          next.committee = event.payload.committee;
          break;
        case "validation":
          next.metrics = event.payload.metrics;
          break;
        default:
          break;
      }
      return next;
    });
  };

  const start = async (payload) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setError("");
    setRun(initialRun);
    setBusy(true);
    try {
      await streamReview(payload, handleEvent, controller.signal);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 lg:p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">
            AI Go/No-Go 심의위원회
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            공공 입찰공고 참여 여부를 영업·기술·재무·법무 4개 관점으로 심의하는 멀티
            에이전트 의사결정 시스템
          </p>
        </div>
        {config && (
          <div className="text-right text-sm text-slate-400">
            <p>
              심의 대상 기업 <span className="font-medium text-slate-200">{config.company.name}</span>
            </p>
          </div>
        )}
      </header>

      <nav className="flex gap-1 border-b border-slate-800 print:hidden">
        {TABS.map((entry) => (
          <button
            key={entry.key}
            onClick={() => setTab(entry.key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              tab === entry.key
                ? "border-sky-500 font-semibold text-slate-100"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300 print:hidden">
          {error}
        </div>
      )}

      {tab === "screen" && (
        <ScreeningView
          corpus={corpus}
          report={report}
          busy={busy}
          onRun={startScreening}
        />
      )}

      {tab === "review" && (
        <ReviewView
          config={config}
          samples={samples}
          run={run}
          busy={busy}
          onRun={start}
          onError={setError}
        />
      )}

      <footer className="pt-2 pb-6 text-center text-xs text-slate-600 print:hidden">
        Project 08 · Multi-Agent Decision Support System for Public Bidding
      </footer>
    </div>
  );
}
