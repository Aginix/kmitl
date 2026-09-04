# A loan references the source document's budget commitment, it never reserves its own

Status: superseded by ADR-0019 (2026-09) — the read-only-snapshot decision no longer holds; the rest of this ADR's reasoning is still current

## Context & Decision

Until now nothing connected a loan to งบประมาณ at all: `advance.payment` carried the four analytic dimensions but no `budget.commitment`, and `advance_payment` did not even declare `budget` in its `depends`. The only budget-adjacent fact was one hop away — `agx_approval_advance_payment` reads the *request's* `budget_commitment_amount` to cap the Borrowing Headroom.

`advance.payment` now stores **`budget_commitment_id`**, copied off the source document when the reference is picked:

- from `approval.request.budget_commitment_id` (`agx_approval_advance_payment`)
- from `purchase.request.budget_commitment_id` (`purchase_request_advance_payment`, both the pull and the push path — ADR-0007 §Consequences records that the two overlap by design)

The loan **does not reserve**. It rides the earmark the source document already reserved.

> Amended by ADR-0009: `budget_commitment_id` and the analytic dimensions now live in the `advance_payment_budget` bridge, not in `advance_payment` itself. Everything below about *what* the field means and *why* it is a copied snapshot is unchanged; only its module home moved.

## Why

- **A loan creating its own commitment would double-reserve the same money.** The source document reserved it once (`purchase.request.action_reserve_budget`, `approval.request.action_reserve_budget`); a second reservation for the cash drawn against that same plan would consume the appropriation twice. This is the recommendation already recorded as parked in `agx_approval` ADR-0003.
- **A snapshot, not a computed mirror.** The source is free to release or re-point its own commitment afterwards (`_cancel_budget_commitment` on PR reject/cancel, `_release_budget_commitment` on AR cancel/draft). A computed field would erase the record of where the cash actually came from at the moment it went out; a stored copy survives. This is the same reason the field is `copy=False` and `readonly`.
- **Only the commitment needs to travel.** The single place that consumes budget — `disbursement.request._action_approve_budget()` — reads the account and the analytic distribution off the commitment's own `reserve` line. So `budget_account_id` and `account_fiscal_year_id` are not needed on the loan.
- `ondelete="restrict"` matches the typed source mirrors (ADR-0007): a commitment that funded a loan cannot be deleted out from under it.

## Consequences

- **Consumption (ตัดงบ) is still parked.** This ADR wires the *carrier* only. Nothing on the loan path obligates or consumes: `disbursement.request._action_approve_budget()` is the only consumer in the system, and a loan never reaches a DR — `agx_approval_disbursement._billable_allocations()` excludes `payment_type == "advance"` rows and skips DR creation entirely when every row is เงินยืม. So an AR funded purely by loans still leaves its commitment `reserved` forever. The settled policy (`agx_approval` ADR-0003) — *budget is used when the cash is transferred out, and returning the leftover returns it to the budget* — remains unmapped onto the จองงบ → ผูกพัน → ตัดงบ stages.
- **Empty for a standalone loan.** A loan with no source document has no commitment to copy, and inventing one would be inventing a policy. `agx_approval` ADR-0003 already records that "standalone loans and their budget source are a separate policy question"; that question is unchanged and now visible as a blank field.
- **The PR path already carries the commitment downstream without help.** A PR-backed loan that later produces a purchase-request approval → DR gets `budget_commitment_id` on the DR from the PR itself (`purchase_request_approval_disbursement_budget`), which is the same commitment the loan now records. No new hand-off was added.
- The field is `readonly` in the UI and hidden when empty, and is **not** added to `_PROTECTED_FIELDS` — `reference`, which it derives from, is already protected, so the value cannot drift by re-pointing the source after submit.
- No dimension-matching risk is introduced: the loan does not call the availability engine, so the all-six-dimensions-or-pinned-False rule (`budget` ADR-0005) does not apply to it. Whoever eventually consumes will inherit the source commitment's own dimensions.
