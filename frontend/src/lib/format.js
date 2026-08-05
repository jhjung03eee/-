export const DECISION_STYLE = {
  GO: {
    label: "GO",
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/40",
    dot: "bg-emerald-400",
  },
  REVIEW: {
    label: "REVIEW",
    text: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/40",
    dot: "bg-amber-400",
  },
  "NO-GO": {
    label: "NO-GO",
    text: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/40",
    dot: "bg-rose-400",
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

export const stars = (count) => "★".repeat(count) + "☆".repeat(Math.max(0, 5 - count));

// Initial + color avatar badges per committee role (no external image assets needed).
export const ROLE_INITIAL = {
  sales: "영",
  technical: "기",
  finance: "재",
  legal: "법",
};

export const ROLE_AVATAR = {
  sales: "bg-sky-500/20 text-sky-300 ring-sky-500/40",
  technical: "bg-violet-500/20 text-violet-300 ring-violet-500/40",
  finance: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40",
  legal: "bg-amber-500/20 text-amber-300 ring-amber-500/40",
};

// Kept for backwards compatibility with any lingering symbol usage.
export const ROLE_ICON = ROLE_INITIAL;

export const CHAIR_INITIAL = "위";
export const CHAIR_AVATAR = "bg-fuchsia-500/20 text-fuchsia-300 ring-fuchsia-500/40";
