export default function Panel({ title, subtitle, actions, children, className = "" }) {
  return (
    <section
      className={`rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur ${className}`}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-800 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase">
              {title}
            </h2>
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
