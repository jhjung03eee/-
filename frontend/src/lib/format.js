export const DECISION_STYLE = {
  GO: {
    label: "GO",
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    dot: "bg-emerald-400",
    icon: "✅",
    glow: "from-emerald-500/20 via-emerald-500/5",
  },
  REVIEW: {
    label: "REVIEW",
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/40",
    dot: "bg-amber-400",
    icon: "⚠️",
    glow: "from-amber-500/20 via-amber-500/5",
  },
  "NO-GO": {
    label: "NO-GO",
    text: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/40",
    dot: "bg-rose-400",
    icon: "⛔",
    glow: "from-rose-500/20 via-rose-500/5",
  },
};

export const decisionStyle = (decision) =>
  DECISION_STYLE[decision] || DECISION_STYLE.REVIEW;

export const krw = (amount) => {
  if (!amount) return "미확인";
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}억원`;
  if (amount >= 1e4) return `${Math.round(amount / 1e4).toLocaleString()}만원`;
  return `${amount.toLocaleString()}원`;
};

export const percent = (value) => `${Math.round((value ?? 0) * 100)}%`;

// Internal scores are stored 0–1; display them as a 10-point "스코어" instead.
export const score10 = (value) => `${((value ?? 0) * 10).toFixed(1)}/10`;

export const stars = (count) => "★".repeat(count) + "☆".repeat(Math.max(0, 5 - count));
