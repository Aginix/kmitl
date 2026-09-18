# Single-draw agreement, serial borrowing, and the request → clear → close lifecycle

Status: proposed (redesign from the 2026-07 requirements review; UAT-only, not yet built)

## Context & Decision

The 2026-07 requirements review described "ทยอยยืม (partial borrowing)". We deliberately do **not** model an agreement as a ceiling with multiple draws. Instead: **one Advance Payment Agreement = one borrower = one disbursement for the exact amount requested.** Multi-activity needs are met by **serial borrowing** (borrow → clear → borrow again), enforced by a **one-active-agreement-per-borrower** rule: global across all loan types, checked at submit, blocking when the borrower already has an agreement in `to_verify` / `to_approve` / `waiting_transfer` / `in_progress`. The rule is global with no exceptions — a Floating Fund (เงินสำรองหมุนเวียน) is **out of scope** for this effort.

The lifecycle is `draft → to_verify → to_approve → waiting_transfer → in_progress → to_verify_report → to_reconcile → done`, with the single negative state `cancel`. (The settle stage — `to_verify_report` / `to_reconcile` — is detailed in ADR-0003.)

## Why

- Matches KMITL policy: the borrower is personally liable (no borrowing on behalf) and the institute wants at most one open debt per person at a time — which a ceiling+draws model would not enforce.
- Keeps the money model simple (one agreement = one debt) and reuses the existing `finance_kmitl` bank-export gate for disbursement.
- Records that the *absence* of multi-draw is deliberate — otherwise a future reader will "fix" it to match the requirements wording.

## Consequences

- **Two numbers.** ADV running number assigned at submit (`draft → to_verify`); a separate **Contract Number** assigned at the **Effective Date** when the transfer completes (a simple running sequence for now; a dedicated override module can customize the format later).
- **Effective Date** (transfer complete) auto-moves `waiting_transfer → in_progress`, creates the debt, and stamps the Contract Number. "ลูกหนี้โดยสมบูรณ์" is the `in_progress` state.
- **Two review stages.** `to_verify` = finance officer checks the paper documents (Verify); `to_approve` = management approval, today a single sign-off by `group_advance_payment_manager` (see ADR-0006).
- **Edit rights before approval.** Material fields (amount, loan type, bank, borrower, department, analytic dimensions, source reference) lock at submit. The creator may still edit `loan_reason` + attachments while in `to_verify`. A `group_advance_payment_loan_officer` (was `group_advance_payment_officer` — renamed by ADR-0010) may reset-to-draft and edit freely while in `to_verify`.
- **Reset to draft (ตั้งกลับเป็นแบบร่าง).** The borrower may pull a not-yet-approved request (`to_verify` / `to_approve`) back to `draft`, keeping the ADV number (`action_recall`). Two more paths reach `draft` under the same UI verb — the loan officer's ส่งกลับแก้ไข from `to_verify` and the manager's un-cancel from `cancel` (ADR-0012); see the CONTEXT.md entry for the split. The domain term is *reset to draft*, not *ดึงกลับ*, which is reserved for e-Saraban (ADR-0011).
- **Clearing is internal.** Debt is cleared across `to_verify_report` / `to_reconcile` by verified actual expenses + returned cash; advance_payment does not use a Disbursement Request (ใบเบิก/DR), and references AR/PR only through bridge modules.
- Largely retains the existing single-amount model, but renames/adds states and moves numbering; the earlier multi-draw exploration is rejected.
