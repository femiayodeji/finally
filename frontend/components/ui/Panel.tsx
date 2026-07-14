interface PanelProps {
  title: string;
  action?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}

/** The one structural device this dashboard uses everywhere: a flat,
 * hairline-bordered section with a small-caps label. No cards, no shadows,
 * no rounded corners — panels tile edge-to-edge like a real terminal. */
export function Panel({ title, action, className = "", bodyClassName = "", children }: PanelProps) {
  return (
    <section className={`flex flex-col bg-panel border border-line ${className}`}>
      <header className="flex shrink-0 items-center justify-between border-b border-line-soft px-3 py-2">
        <h2 className="font-display text-[11px] font-medium uppercase tracking-[0.14em] text-ink-dim">
          {title}
        </h2>
        {action}
      </header>
      <div className={`min-h-0 flex-1 ${bodyClassName}`}>{children}</div>
    </section>
  );
}
