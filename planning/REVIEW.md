# Review Feedback (since last commit)

## Scope Reviewed
- Changed tracked file: `planning/PLAN.md`
- Untracked paths (`.claude/agents/`, `.claude/commands/`) were not reviewed as they are not part of `git diff` from last commit.

## Overall Assessment
`planning/PLAN.md` is materially improved. The revision resolves previous ambiguities and aligns the architecture around a clear server-authoritative model. The document now reads as a coherent technical plan instead of a collection of loosely coupled decisions.

## What’s Strong

1. **Clear architectural principle added**
   - The new “Backend Owns the Core” section is a strong anchor. It clarifies ownership of valuation, P&L, price history, and change % in one place, and it explains why.

2. **Inconsistencies were resolved concretely**
   - Tracked ticker set now explicitly covers `watchlist ∪ open positions`.
   - Unknown ticker behavior is now mode-specific (simulator accepts + seeds defaults; Massive rejects unpriceable symbols).
   - Startup initialization timing is no longer ambiguous.
   - `watchlist_changes.action` values and position-close semantics are now explicit.

3. **Frontend/backend contract is much cleaner**
   - The plan now clearly distinguishes initial REST snapshot vs SSE live source of truth.
   - Backend-computed change % + history endpoint definition gives deterministic cross-tab behavior and stable reload semantics.

4. **Good practical tradeoff documented**
   - Keeping short-term tick history in memory (not SQLite) is the right low-latency call for this demo scope, and the rationale is documented.

5. **Decision log quality is high**
   - “Resolved Design Decisions” is useful and auditable; it ties outcomes to sections and records rationale.

## Remaining Gaps / Risks

1. **Potential duplication/drift risk**
   - Some decisions are now stated in multiple places (core sections + section 13). This is useful now, but it increases maintenance risk if one part changes later.
   - Suggestion: keep section 13 as a concise changelog-style index and make canonical rules live only in core sections.

2. **Session reference price semantics could be sharper**
   - “Captured on first observation after process start” is clear, but still leaves edge cases implicit (e.g., ticker added long after startup; symbol removed then re-added).
   - Suggestion: explicitly state whether “session open” is per-process-per-symbol first-seen and whether it resets on symbol eviction or only process restart.

3. **History endpoint behavior needs explicit API contract detail**
   - The document names `GET /api/prices/{ticker}/history`, but does not specify request/response details, max points, sort order, and empty-history behavior.
   - Suggestion: add exact response schema + guarantees (ascending timestamps, bounded length, default/optional `limit`, behavior for unknown ticker).

4. **Money precision policy may need one extra rule**
   - Rounding to cents at execution is defined, which is good.
   - Suggestion: also state the rounding mode (e.g., half-up vs banker’s) and where else rounding is applied (display-only vs stored values) to avoid subtle inconsistencies.

5. **SSE reliability policy is lightly specified**
   - “SSE resilience: disconnect and verify reconnection” appears in testing, but reconnection/backfill semantics aren’t fully defined.
   - Suggestion: define whether reconnect triggers history backfill fetch, how missed ticks are handled, and if event IDs/replay are in scope.

## Suggested Next Edits (Small, High-Value)
- Add a compact API contract block for `GET /api/prices/{ticker}/history`.
- Add one paragraph defining session reference price lifecycle edge cases.
- Add explicit monetary rounding mode and storage/display policy line.
- Keep section 13 but trim repetitive prose where it duplicates canonical sections.

## Verdict
**Approve with minor documentation follow-ups.**

The updated plan is directionally strong and substantially less ambiguous than before. The remaining issues are mostly contract precision/details, not architectural flaws.
