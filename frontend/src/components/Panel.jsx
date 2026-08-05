export default function Panel({ title, subtitle, actions, children, className = "" }) {
  return (
    <section
      className={`rounded-lg border border-slate-800/90 bg-slate-900/55 shadow-[0_10px_30px_rgb(0_0_0_/_0.12)] ${className}`}
    >
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-800/90 px-4 py-3.5">
          <div>
            <h2 className="text-base font-semibold text-slate-100">
              {title}
            </h2>
            {subtitle && <p className="mt-0.5 text-sm text-slate-400">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
