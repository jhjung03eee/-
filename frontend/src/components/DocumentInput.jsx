import { useRef, useState } from "react";
import { uploadDocument } from "../lib/api";
import Panel from "./Panel";

export default function DocumentInput({ samples, running, onRun, onError }) {
  const [sampleId, setSampleId] = useState("");
  const [text, setText] = useState("");
  const [name, setName] = useState("bid-notice.md");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const pickSample = (id) => {
    setSampleId(id);
    setText("");
    setName(id ? `${id}.md` : "bid-notice.md");
  };

  const handleFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadDocument(file);
      setText(result.markdown);
      setName(result.document_name);
      setSampleId("");
    } catch (error) {
      onError(error.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const submit = () => {
    if (sampleId) return onRun({ sample_id: sampleId });
    if (text.trim()) return onRun({ document_text: text, document_name: name });
    onError("샘플을 선택하거나 공고문을 입력하세요.");
  };

  return (
    <Panel title="입찰공고 입력" subtitle="샘플 선택 · PDF/Markdown 업로드 · 직접 붙여넣기">
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="space-y-3 rounded-md border border-slate-800 bg-slate-950/30 p-3">
          <div>
            <label className="mb-1.5 block text-sm text-slate-400">샘플 공고</label>
            <select
              value={sampleId}
              onChange={(e) => pickSample(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15"
            >
              <option value="">— 선택 안 함 —</option>
              {samples.map((sample) => (
                <option key={sample.id} value={sample.id}>
                  {sample.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-slate-400">파일 업로드</label>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.md,.markdown,.txt"
              onChange={handleFile}
              className="w-full cursor-pointer rounded-md border border-slate-700 bg-slate-900 text-sm text-slate-400 file:mr-3 file:cursor-pointer file:rounded-l-md file:border-0 file:bg-slate-800 file:px-3 file:py-2 file:text-slate-300"
            />
            {uploading && <p className="mt-1 text-xs text-sky-400">문서 변환 중…</p>}
          </div>

          <button
            onClick={submit}
            disabled={running || uploading}
            className="w-full rounded-md bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_4px_14px_rgb(2_132_199_/_0.25)] transition hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-400 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500 disabled:shadow-none"
          >
            {running ? "심의 진행 중…" : "위원회 심의 시작"}
          </button>
        </div>

        <div className="min-w-0">
          <label className="mb-1.5 block text-sm text-slate-400">
            공고문 원문 {sampleId && "(샘플 선택 시 서버에서 로드)"}
          </label>
          <textarea
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (e.target.value) setSampleId("");
            }}
            placeholder="공고문 마크다운을 붙여넣거나 위에서 파일을 업로드하세요."
            className="h-52 w-full resize-none rounded-md border border-slate-700 bg-slate-950 p-3 font-mono text-xs leading-relaxed text-slate-300 outline-none transition placeholder:text-slate-600 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15"
          />
        </div>
      </div>
    </Panel>
  );
}
