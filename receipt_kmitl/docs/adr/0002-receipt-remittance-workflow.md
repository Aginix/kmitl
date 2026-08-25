# Receipt Remittance workflow: per-receipt detach instead of batch reject

`kmitl.receipt.remittance` (รายงานนำส่งคลัง — the renamed `kmitl.cash.deposit`)
is the document a department submits to remit its confirmed receipts to the
central treasury. It follows an HR-expense-sheet-like flow but deliberately omits
a whole-document reject/reset, because a remittance can carry hundreds of receipts
and an error usually affects only a few.

## Workflow

- States: `draft → submitted → done` (+ `cancelled`). No approval step.
- `submitted`: department action; stamps `date` = the actual submission date and
  mints the number `RM/<FY>/nnnn` where `<FY>` is the 4-digit Buddhist-era fiscal
  year of that date. Header becomes read-only.
- `done`: central treasury (finance) action; creates one accounting entry per
  receipt and marks each receipt `posted`.
- **Once `submitted`, a remittance can never be reset to `draft`.**

## Error correction — detach, not reject

- Both the owning department and central finance may **detach** individual
  receipts from a `submitted` remittance (a per-row button, guarded in code;
  logged to chatter on both sides). Detach is only allowed when the remittance
  is in the `submitted` state — not `draft` (use the o2m to remove rows instead)
  and not `done` (posted receipts are immutable). A detached receipt drops back
  to the unremitted `confirmed` pool, keeping its number, and is corrected
  (reset → edit → re-confirm) then remitted in a **later** remittance. The
  original remittance proceeds to `done` with the receipts that remain.
- The only whole-document escape hatch is `cancel` (allowed from `draft`/
  `submitted`, not `done`), which releases every receipt back to the pool.

## Scope of a remittance

- A remittance names one `department_analytic_id`; it pulls and validates
  receipts by `child_of` that department, so a parent (rollup) department gathers
  all sub-department receipts. Department here is a business/bundling dimension,
  not access control (see ADR-0001).

## Why

Whole-batch reject/reset was rejected: with many receipts per remittance it forces
a unit to re-do good work for one bad receipt. Detach gives receipt-level
granularity that units and treasury can drive themselves, while keeping the
submitted document immutable as an audit anchor. Requirements for this process
are still provisional — this is the minimum viable shape, chosen to be extendable
(an approval stage can be inserted between `submitted` and `done` later).
