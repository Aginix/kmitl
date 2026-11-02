# ADR-0011: ถัวจ่าย on the approval request, entered on its ใบจองงบประมาณ

## Status

Accepted (2026-11-02). Applies budget [ADR-0020](../../../budget/docs/adr/0020-cross-charge-entered-on-the-reservation-form.md)
(ถัวจ่าย on the พ.1) to the คำขออนุมัติ, with two deliberate differences.

## Decision

- **Same shape as the พ.1.** The request keeps one code, the Primary Code. The ถัว codes
  live on its ใบจองงบประมาณ (Reservation Split). ยืนยันงบประมาณ opens that slip as a
  dialog, as a draft built from the request; ยืนยันจองงบประมาณ reserves every row and
  sends the request to รอส่งขออนุมัติ. ปิด leaves a draft slip, which reserves nothing
  and is reused by the next press. Packaged as the auto-install add-on
  `agx_approval_budget_cross_charge`; without it nothing changes.
- **Who and what.** Only the Budget Confirmer edits, and they can change the split, the
  Primary Code and the four dimensions. The วงเงิน stays the request total. Saving a
  reserved slip re-cuts it in one step and copies the code and dimensions back to the
  request.
- **Difference 1 — ถัว codes must be Approval-eligible.** A ถัว code must be flagged
  ถัวจ่ายได้ **and** `approval_ok`. On the พ.1, a ถัว code need not be `purchase_ok`. A
  ถัว code need not fall under the category's pinned code; the Primary Code keeps
  [ADR-0004](0004-budget-code-selection-scoped-by-category-non-procurement.md)'s rules.
- **Difference 2 — the returned window.** Edit windows: a draft slip at รอยืนยันงบประมาณ;
  a reserved, unused slip at รอส่งขออนุมัติ, **or** at ตีกลับ when e-Saraban sent the
  letter back (ตีกลับ/ดึงกลับ). The พ.1 locks once its letter is sent. The approval letter
  renders its budget table live, so the re-sent letter shows the new split. A request
  returned from a disbursement (its letter completed) stays locked, and so does
  ส่งขออนุมัติแล้ว.
- **Disbursement is unchanged.** A ใบขอเบิก still names only the Primary Code; the budget
  ledger charges the codes in order (budget ADR-0018). The approval letter lists every
  code with its amount.
- Draw-down and project modes never split: the slip belongs to its owner.

## Considered options

- **A ถัว grid on the request, or one code per Expense** — rejected: every consumer of
  the slip would need a second source (ADR-0020 D1).
- **Locking from ส่งขออนุมัติแล้ว on, like the พ.1** — rejected: a letter sent back for
  revision is exactly when the signers ask for a different split.

## Consequences

- Core `agx_approval` treats a draft slip like a cancelled one (nothing reserved), so the
  ยืนยันงบประมาณ button and budget fields stay open while one is linked.
- The owner guard moved into `budget_commitment_cross_charge`, so the พ.1 and the
  request share it (see the ADR-0020 consequence of 2026-11-02).
