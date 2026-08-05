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

export const ROLE_ICON = {
  sales: "◈",
  technical: "⚙",
  finance: "₩",
  legal: "§",
};
