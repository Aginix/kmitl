# Settlement and close: expense report → leftover → reconcile → close

Status: proposed (2026-07 review; UAT-only)

## Context & Decision

After disbursement (`in_progress`), the debt is settled and the agreement closed through **two explicit states**:

- **`to_verify_report` (รอตรวจรับรายงาน)** — the borrower records an **actual-expense summary directly on the agreement** (description, actual expense amount, auto-computed return amount = loan − actual expense, and evidence — **no itemized lines**) and submits it. The loan-responsible finance officer **accepts** it. If the return amount = 0, the officer **manually closes** → `done`; otherwise → `to_reconcile`.
- **`to_reconcile` (รอตรวจสอบเงินคืน)** — the borrower returns the money and records each transfer (amount = the real transfer); finance **reconciles** each against the bank. A **`return_installment` flag** (borrower-set at report time, officer-adjustable for emergencies) governs the shape: **off (default)** = a single return equal to the return amount; **on** = multiple partial returns that accumulate to it. When the reconciled returns cover the amount owed (debt = 0) the agreement **auto-closes** → `done`. **Over-return** (a return, or the cumulative total, exceeds the amount owed) requires the borrower to **confirm donating the excess** — mandatory consent + audit trail — before close; the excess is never refunded. **No receipt is required to close.**

If the borrower never returns the money, the agreement simply stays in `to_reconcile` (no force-close); follow-up is by notification.

## Why

- Two explicit states make the current stage legible to staff (report acceptance vs money-back verification) — chosen over a single `waiting_return` with hidden sub-steps.
- Auto-close only on an exact reconcile keeps the operational debt figure trustworthy without accounting integration (ADR-0002).
- Donation-only for the excess avoids spawning an outbound refund payment and matches institute practice; consent + audit gives the legal trail.

## Consequences

- Two finance touchpoints: the loan-responsible officer (accept report / close-when-zero) and finance/treasury (reconcile returned cash). Role → group mapping is TBD.
- `to_verify_report` has two exits (→ `done` when Leftover 0; → `to_reconcile` when Leftover > 0).
- Removes the old "close with remaining > 0" confirm wizard — closing with outstanding debt is no longer allowed.
- The actual-expense summary is fields on the agreement (`actual_expense_amount`, `expense_description`, computed `return_amount`, evidence); the old itemized `usage_line` model is **removed**. Accounting entries for expenses remain out of scope (ADR-0002).
- `return_installment` (off by default) restricts `to_reconcile` to a single return equal to the amount owed; on allows multiple accumulating returns. The officer may toggle it in emergencies.
