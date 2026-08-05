const SKIN = "#f6c9a0";
const BLUSH = "#ff9d9d";
const INK = "#3a2a1d";

const BG = {
  sales: "#38bdf8",
  technical: "#a78bfa",
  finance: "#34d399",
  legal: "#fbbf24",
  chair: "#e879f9",
};

function Face() {
  return (
    <>
      <circle cx="24" cy="27" r="13.5" fill={SKIN} />
      <ellipse cx="15.5" cy="30" rx="2.2" ry="1.3" fill={BLUSH} opacity="0.7" />
      <ellipse cx="32.5" cy="30" rx="2.2" ry="1.3" fill={BLUSH} opacity="0.7" />
      <circle cx="19" cy="26.5" r="1.6" fill={INK} />
      <circle cx="29" cy="26.5" r="1.6" fill={INK} />
      <path d="M19.5 32c1.6 1.8 7.4 1.8 9 0" stroke={INK} strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </>
  );
}

// 영업 위원 — side-parted hair + red necktie
function Sales() {
  return (
    <>
      <path d="M11 22c0-8 6-13 13-13s13 5 13 13c-2-2-6-3-9-2-3-4-9-4-13-1-2 1-3.5 2-4 3z" fill="#1e3a5f" />
      <path d="M21 38l3 5 3-5-1.5-2h-3z" fill="#dc2626" />
      <rect x="22" y="35" width="4" height="3" fill="#fff" />
    </>
  );
}

// 기술 위원 — hard hat + round glasses
function Technical() {
  return (
    <>
      <path d="M10 21a14 14 0 0 1 28 0z" fill="#facc15" />
      <rect x="9" y="20" width="30" height="3.4" rx="1.5" fill="#eab308" />
      <rect x="21" y="10" width="6" height="4" rx="1" fill="#eab308" />
      <circle cx="18.5" cy="27" r="4.2" fill="none" stroke="#4c1d95" strokeWidth="1.6" />
      <circle cx="29.5" cy="27" r="4.2" fill="none" stroke="#4c1d95" strokeWidth="1.6" />
      <path d="M22.7 27h2.6" stroke="#4c1d95" strokeWidth="1.6" />
    </>
  );
}

// 재무 위원 — neat hair + square glasses + coin pin
function Finance() {
  return (
    <>
      <path d="M11 24c-1-9 5-15 13-15s14 6 13 15c-3-5-8-7-13-7s-10 2-13 7z" fill="#4b3221" />
      <rect x="15.5" y="24" width="8" height="6" rx="1.4" fill="none" stroke="#1f2937" strokeWidth="1.6" />
      <rect x="24.5" y="24" width="8" height="6" rx="1.4" fill="none" stroke="#1f2937" strokeWidth="1.6" />
      <path d="M23.5 27h1" stroke="#1f2937" strokeWidth="1.6" />
      <circle cx="24" cy="39" r="4" fill="#facc15" stroke="#b45309" strokeWidth="1" />
      <text x="24" y="41.5" fontSize="5" textAnchor="middle" fill="#7c2d12" fontWeight="700">
        ₩
      </text>
    </>
  );
}

// 법무 위원 — silver hair + scales of justice
function Legal() {
  return (
    <>
      <path d="M11 23c-1-8 5-14 13-14s14 6 13 14c-3-4-8-6-13-6s-10 2-13 6z" fill="#9ca3af" />
      <rect x="16" y="24.5" width="7.4" height="5.6" rx="1.3" fill="none" stroke="#1f2937" strokeWidth="1.6" />
      <rect x="24.6" y="24.5" width="7.4" height="5.6" rx="1.3" fill="none" stroke="#1f2937" strokeWidth="1.6" />
      <line x1="24" y1="7" x2="24" y2="16" stroke="#78350f" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="17" y1="10.5" x2="31" y2="10.5" stroke="#78350f" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M17 10.5l-3 5h6z" fill="none" stroke="#78350f" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M31 10.5l-3 5h6z" fill="none" stroke="#78350f" strokeWidth="1.4" strokeLinejoin="round" />
    </>
  );
}

// 위원장 — dark hair + gold crown
function Chair() {
  return (
    <>
      <path d="M11 24c-1-9 5-15 13-15s14 6 13 15c-3-5-8-7-13-7s-10 2-13 7z" fill="#312244" />
      <path
        d="M13 14l3.5 5 7.5-7 7.5 7 3.5-5v6h-22z"
        fill="#facc15"
        stroke="#b45309"
        strokeWidth="1"
        strokeLinejoin="round"
      />
      <circle cx="24" cy="12.5" r="1.3" fill="#f87171" />
    </>
  );
}

const ROLE_ART = {
  sales: Sales,
  technical: Technical,
  finance: Finance,
  legal: Legal,
  chair: Chair,
};

export default function CommitteeAvatar({ role, size = 44, className = "" }) {
  const Art = ROLE_ART[role] || Sales;
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      className={`shrink-0 rounded-full ${className}`}
      style={{ backgroundColor: BG[role] || BG.sales }}
      role="img"
      aria-label={`${role} avatar`}
    >
      <Face />
      <Art />
    </svg>
  );
}
