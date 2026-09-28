# Breakdown nests budget accounts under the exact tagged dimension tuple

The budget monitoring dashboard (and the reservation picker, which reuses its
grid) can optionally nest the budget-account tree under an **ordered list of
financial dimensions** — `breakdown` is a list of dim fields, e.g.
`["department_analytic_id", "activity_analytic_id"]` (departments outer,
activities inner). Each dimension forms a hierarchy level; the account tree
hangs off the innermost one. Under each **exact** dimension node we nest the
next dimension (or the account tree) only for lines tagged to that exact node —
never rolled down from an ancestor — so the "exact node" is the exact N-tuple.
A node's figure is the sum over its whole remaining subtree, so every level
reconciles with the flat report. Started single-dimension (activities); now
generalized to N (added departments).

## Considered Options

- **Exact-match nesting, applied at every level (chosen).** A dimension node's
  total = its own exact-tuple content + its child-node totals. Summing over a
  level partitions the parent, so every level (and the whole view) reconciles
  with the flat report, and no money is shown twice.
- **Rolled nesting (rejected).** Show the full subtree under *every* node,
  summing descendants. Rejected because it presents the same leaf money under
  each ancestor (double-reading).

## Consequences

- Untagged values at any level fall into a per-level "ไม่ระบุ" sentinel (id 0),
  shown only when such lines exist, so the breakdown still reconciles. Real
  KMITL data always carries all dimensions, so the sentinel is invisible
  insurance.
- A reservation maps to **one dimension tuple**: the picker sources each
  broken-down dimension from the picked row and blocks picks that span more than
  one tuple or sit under a sentinel. This keeps the header-level engine
  coherent — `cap` (read from the reserve line's stored dimension fields) and
  obligate/consume (which copy the header distribution) all stay on one tuple.
  A commitment whose reserve lines somehow span >1 tuple is logged, not split.
- Rows are keyed by a path-encoded `key`/`parent_key` (`a<id>|p<id>|b<id>`), so
  one budget account can appear under several tuples; each row carries a
  `dims` (field→id) map + `dim_level`. The reservation picker still selects by
  budget-account id.

## Amendment (ADR-0016)

A hierarchical dimension filter on the picker feed (`get_reservation_grid`) always matches pools that **cover** the typed code (its ancestors as well as its `child_of` subtree). A breakdown row's dimension tuple may then be an *ancestor* of what the user typed; the reservation pins the **finer** of the row value and the filter value (the client uses the returned `filter_ancestors`). Account rows also carry `own_current` (own posted appropriation at the exact tuple) so the picker can tell a real pool row from a pure roll-up, plus `account_narrowable` / `narrow_required` flags for the descendant-code autocomplete.

**Usage is read at its pool.** Exact-match nesting still places *appropriation* on the tuple it was tagged to, but *usage* (cap, reserve, obligate, consume, return) booked at a Descendant Code is folded onto the tuple of the Budget Pool that covers it — keeping its own budget account, so the account tree under that tuple rolls it up to the pool's account. Without this a pool row showed its full คงเหลือ while the descendant row went negative. The fold runs on the full four-dimension tuple (deepest covering pool first, as the engine's control node) and only then projects onto the chosen breakdown, so the flat report and every breakdown reconcile. Usage that no pool covers stays on its own tuple (negative คงเหลือ = 0 available). A hierarchical filter now covers on the dashboard too: the pools funded above the typed code appear, each with the usage of every code under it, siblings included, so a sub-unit sees what it can still reserve. Rows whose usage was folded carry `usage_in` / `usage_out` coordinate pairs so the usage drill-down lists exactly the lines behind the figure.

- **Considered:** show the reservation on both the pool row and the descendant row (rejected — reads money twice, the thing this ADR forbids); keep exact nesting and add a "remaining at pool" column (rejected — the pool row still reads full); resolve each usage coordinate through `budget.controller` (rejected — one query per coordinate on a report of thousands).
- **Consequence:** the breakdown no longer shows *who* reserved under a coarse pool (e.g. which ภาควิชา); the usage drill-down does.
