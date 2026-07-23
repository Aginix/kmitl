# Settlement and close: expense report → leftover → reconcile → close

Status: proposed (2026-07 review; UAT-only)

## Context & Decision

After disbursement (`in_progress`), the debt is settled and the agreement closed through **two explicit states**:

- **`to_verify_report` (รอตรวจรับรายงาน)** — the borrower submits an **Expense Report** (actual expenses + evidence; Leftover = loan − expenses). The loan-responsible finance officer **accepts** it. If Leftover = 0, the officer **manually closes** → `done`. If Leftover > 0 → `to_reconcile`.
- **`to_reconcile` (รอตรวจสอบเงินคืน)** — the borrower returns the Leftover in **one or more partial transfers**, recording each return (amount = the real transfer); finance **reconciles** each against the bank. When the reconciled returns **cumulatively cover the Leftover** (debt = 0) the agreement **auto-closes** → `done`; until then it stays pending. **Over-return** (a single return, or the cumulative total, exceeds the Leftover) requires the borrower to **confirm donating the excess** to the institute — mandatory consent + audit trail — before close; the excess is never refunded. **No receipt is required to close.**

If the borrower never returns the money, the agreement simply stays in `to_reconcile` (no force-close); follow-up is by notification.

## Why

- Two explicit states make the current stage legible to staff (report acceptance vs money-back verification) — chosen over a single `waiting_return` with hidden sub-steps.
- Auto-close only on an exact reconcile keeps the operational debt figure trustworthy without accounting integration (ADR-0002).
- Donation-only for the excess avoids spawning an outbound refund payment and matches institute practice; consent + audit gives the legal trail.

## Consequences

- Two finance touchpoints: the loan-responsible officer (accept report / close-when-zero) and finance/treasury (reconcile returned cash). Role → group mapping is TBD.
- `to_verify_report` has two exits (→ `done` when Leftover 0; → `to_reconcile` when Leftover > 0).
- Removes the old "close with remaining > 0" confirm wizard — closing with outstanding debt is no longer allowed.
- No receipt (ใบเสร็จรับเงิน) is required to close — resolved: not needed even for an exact return (9A).
- `to_reconcile` accepts **multiple partial return records** (as the existing return lines already allow); close fires when the reconciled total equals the Leftover.
- The Expense Report evolves the old free-form `usage_line`; accounting entries for expenses are out of scope (ADR-0002).
