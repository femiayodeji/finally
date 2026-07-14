import { Panel } from "./Panel";

/** Centered empty-state treatment shared by all non-interactive panels this
 * phase (Positions/Heatmap/P&L/AI Assistant), per 01-UI-SPEC.md "Placeholder
 * panel copy" — identical Heading(18/600, neutral) + Body(12px Label,
 * neutral, dimmer) pattern, no icons/illustrations. */
export function PlaceholderPanel({
  heading,
  body,
  className = "",
  footer,
}: {
  heading: string;
  body: string;
  className?: string;
  /** AI Assistant's grayed, non-interactive input bar preview. */
  footer?: React.ReactNode;
}) {
  return (
    <Panel className={`items-center justify-center text-center ${className}`}>
      <h3 className="text-lg font-semibold text-neutral">{heading}</h3>
      <p className="mt-1 max-w-xs text-xs text-neutral opacity-70">{body}</p>
      {footer}
    </Panel>
  );
}
