/** Shared surface for every panel in the terminal grid (01-UI-SPEC.md
 * "Design System" / "Layout shell"): bg-panel, 1px border-muted, 6px radius,
 * 16px internal padding. Optional title renders as Heading role (18/600). */
export function Panel({
  title,
  className = "",
  children,
}: {
  title?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`flex flex-col rounded-panel border border-border-muted bg-panel p-4 ${className}`}
    >
      {title && <h2 className="mb-3 text-lg font-semibold">{title}</h2>}
      {children}
    </div>
  );
}
