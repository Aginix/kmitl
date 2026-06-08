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
