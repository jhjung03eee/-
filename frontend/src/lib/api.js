const BASE = import.meta.env.VITE_API_BASE || "";

async function json(path, options) {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `요청 실패 (${response.status})`);
  }
  return response.json();
}

export const getConfig = () => json("/api/config");
export const getSamples = () => json("/api/samples");
export const getCorpus = () => json("/api/corpus");
export const runScreening = () => json("/api/screen", { method: "POST" });

export const uploadDocument = (file) => {
  const body = new FormData();
  body.append("file", file);
  return json("/api/upload", { method: "POST", body });
};

export const runReview = (payload) =>
  json("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

/**
 * Streams workflow events. Falls back to the single-shot endpoint when the
 * host buffers the response (some serverless platforms do).
 */
export async function streamReview(payload, onEvent, signal) {
  const response = await fetch(`${BASE}/api/review/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok || !response.body) {
    const result = await runReview(payload);
    onEvent({ stage: "completed", message: "심의 완료", payload: result });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("");
      if (data) onEvent(JSON.parse(data));
      boundary = buffer.indexOf("\n\n");
    }
  }
}
