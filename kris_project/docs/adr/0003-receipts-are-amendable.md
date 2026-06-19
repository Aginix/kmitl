# Receipts are amendable, not immutable

A **Receipt** (`kris.project.receipt`) records a single payment received against a project. It is **amendable** — any business field can be edited after creation — while its project is `draft` or `in_progress`, and **frozen** once the project reaches `done` or `cancel`. `project_id` is the only field locked for the receipt's whole lifetime: a receipt belongs to one project for life.

Editability follows exactly the existing rule for *adding* and *deleting* receipts (the "Add Revenue" button and trash icon are already hidden on `done`/`cancel`). Net effect: while the project is open, KRIS Officers can correct any receipt freely; once the project closes, every money figure on it is locked.

## Why record this

A Receipt looks like an accounting document, and accounting documents are conventionally immutable — the historical default in this module agreed (every field on the form was `readonly="1"`, and the only "edit" path was delete + recreate). We have reversed that default.

The original immutability assumed receipts would be entered once and never need correction. In practice KRIS Officers hit this regularly: typo in the receipt number, wrong date, amount off by a digit, allocation split to the wrong line. Forcing delete + recreate for these cases means re-keying the whole allocation breakdown, which is itself error-prone — the cure was worse than the disease.

We keep the freeze on `done`/`cancel` so the rule "**when a project closes, its money figures stop moving**" still holds. This is the same invariant ADR-0001 relies on when it permits under-collected closure: closure is a discretionary point in time, and Revenue at that point is whatever the open-state edits added up to.

## Considered Options

- **Keep immutable; require delete + recreate** — the prior design. Rejected: the dominant edit case is data correction, where delete + recreate destroys the allocation breakdown the user is *trying to preserve*. Audit clarity from "a receipt never changes" is real but cheap to recover via `mail.thread` field tracking.
- **Edit Wizard mirroring the create wizard** — rejected: the create wizard's value is its *pre-fill* of outstanding amount per installment, which only makes sense at creation. At edit time the receipt already has its values; a wizard would just re-render the form view inside a modal with no added logic.
- **Editable in every state, including `done`/`cancel`** — rejected: it would let a closed project's Revenue total drift after closure. KRIS Admin already has the `cancel → draft` reset path (`action_draft`) for the rare case a closed project legitimately needs correction; that route reopens the project explicitly rather than silently mutating closed data.
- **One2many audit on `allocation_ids`** — deferred. Tracking allocation row changes requires overriding write/create/unlink on the child model and posting messages by hand. The existing `_check_actual_not_exceed_estimated` constraint already prevents the only allocation mistake that has real money consequences; field-level tracking on the parent Receipt covers the typical dispute case.

## Consequences

- `kris.project.receipt` exposes `tracking=True` on the fields that move money or change meaning (`name`, `date`, `equipment_cost_in_installment`, `amount`, `extra_income`, `installment_id`, `note`); audit trail is via chatter, not via row-level history.
- The constraints `_check_extra_income_total` (receipt) and `_check_actual_not_exceed_estimated` (allocation) now fire on edit as well as on create — they were already correct for both paths, no extra logic needed.
- Computed `actual_amount` on `kris.project.allocation.line` recomputes automatically on receipt-allocation writes via its existing `@api.depends`; the explicit `_compute_actual_amount()` call in `KrisProjectReceipt.unlink` is now strictly a safety net, not load-bearing.
- Moving a Receipt between `installment_id` values is allowed and shifts the computed `state` (`pending` / `partial` / `received`) on both the old and new installment. This is the intended behaviour — correcting an installment assignment is one of the cases that drove this decision.
- `project_id` stays hard-readonly in the view. Moving a Receipt across projects would invalidate every `allocation_ids` row (each points at an `allocation_line_id` belonging to the original project) and is not a meaningful edit; the right answer there remains delete + recreate under the correct project.
