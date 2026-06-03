# Activity breakdown nests budget accounts under the exact tagged activity

The budget monitoring dashboard can optionally make a financial dimension
(first: Activity) the outer row axis, with the budget-account tree nested
underneath. Under each activity we show the account subtree only for lines
tagged to that **exact** activity — never rolled down from an ancestor
activity — and both the activity tree and the per-activity account tree roll
up independently.

## Considered Options

- **Exact-match nesting (chosen).** An activity's total = its own
  (exact-match) account rows + its child-activity totals. Every metric
  reconciles to the flat report by summing over the breakdown dimension, and
  no money is shown twice.
- **Rolled nesting (rejected).** Show the full account subtree under *every*
  activity, summing all descendant activities. Rejected because it presents
  the same leaf money under each ancestor (double-reading) and contradicts the
  agreed example.

## Consequences

- Untagged lines fall into a sentinel "ไม่ระบุ" node (shown only when such
  lines exist) so the breakdown still reconciles with the flat report.
- The `cap` column's activity is taken from the commitment's posted reserve
  line (stored), not the non-stored header dimension, so cap co-locates with
  `reserved`.
- Dashboard rows are keyed by a composite `key`/`parent_key` (a budget account
  can appear under several activities); the reservation picker still selects by
  budget-account id.
