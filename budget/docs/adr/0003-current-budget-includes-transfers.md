# Current Budget includes transfers via move_type, not appropriation_type

**Current Budget (a)** is the net of posted `budget.move.line.balance` whose `move_type` is `appropriation` or `entry` — so budget transfers (`budget.transfer`, which post `entry` moves) are included. It is **not** keyed on `appropriation_type`, even though the original spec text defined (a) as `appropriation_type in (initial, supplementary)`.

`appropriation_type` is used only to split out the **Initial (1)** column (`move_type=appropriation` AND `appropriation_type=initial`). Everything else in (a) — supplementary appropriations and net transfers — falls into the **Adjustment (±)** column = (a) − (1).

## Why deviate from the literal spec

- Transfers post `entry` moves with no `appropriation_type`; keying (a) on `appropriation_type` would silently drop transferred budget from the pool.
- It matches the existing `budget.controller` availability engine, which already sums `move_type in (appropriation, entry)`.
