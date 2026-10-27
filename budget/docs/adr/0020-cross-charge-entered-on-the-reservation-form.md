# ถัวจ่าย is entered on the ใบจองงบประมาณ form, as a Reservation Split

## Status

Accepted. Amends [ADR-0006](0006-reservation-reserve-lines-cross-charge.md) and root
[ADR-0010](../../../docs/adr/0010-pr-split-verify-and-budget-commit-direct-entry.md).

## Context

A พ.1 carries exactly one รหัสงบประมาณ, and Reserve built a one-code ใบจองงบประมาณ behind
the scenes. Users need **ถัวจ่าย**: one พ.1 funded from several codes, with a รหัสหลัก,
the same dimensions on every code, and ถัว codes limited to codes that have budget.

The engine already copes with several codes: availability is checked per pool
(ADR-0016) and every later event is liquidated per code, primary first (ADR-0018). What
was missing is a place to **declare** the codes. Reserve events cannot be that place:
an event is immutable from the moment it is created, even on a draft slip (ADR-0017).

## Decision

- **D1. ถัวจ่าย is entered on the ใบจองงบประมาณ, not on the พ.1.** The พ.1 keeps one
  code, the **Primary Code** (รหัสหลัก). Its dimensions and code are still entered on
  the พ.1, by the verifier and then the budget committer (root ADR-0010 is unchanged
  there).
- **D6. The `cross_chargeable` flag governs eligibility** (ADR-0006 stands). A ถัว code
  must be flagged, budgetable, an expense code, and funded at the slip's dimensions
  (Available > 0). The Primary Code must be flagged too once there is more than one
  code. Admins tick the flag on the budget account form and list, and through
  `budget_account_mass_edit`.
- **P1. The form gets a รายการจองงบประมาณ grid**, backed by a new
  `budget.commitment.split` (the **Reservation Split**). Row ★ is the Primary Code; its
  amount is **computed** as วงเงิน − Σ ถัว rows and read-only (D-remainder), so the
  total always equals the วงเงิน. Each row shows งบที่จองได้ and a sufficiency mark,
  and a banner names every row that is short. Once reserved the row also shows its
  code's จองเงิน / ผูกพัน / เบิกจ่าย / คงเหลือ, read from the ledger.
  - จองงบ derives one reserve event per row, primary first, so ADR-0018's liquidation
    order is the split's order. A slip with no split rows reserves from its header
    exactly as before.
  - Re-cutting a reserved split cancels the reserve events and posts new ones, after
    re-checking every pool with the slip's own reservation given back. It is allowed
    only while nothing has been obligated, consumed or returned.
- **P2. Reserve on a พ.1 opens the same form as a dialog** (D-form). The button creates
  — or refreshes, when one was left behind — a **draft** slip from the พ.1: ปีงบ,
  dimensions, Primary Code and วงเงิน = the พ.1 total, all locked in the dialog. To
  change them, close the dialog, edit the พ.1 and press Reserve again. ยืนยันจองงบประมาณ
  reserves every row at once and advances the พ.1; ปิด leaves a harmless draft (a draft
  locks no budget). The single-code case is the same dialog with one row, which gives
  ADR-0010's planned ตรวจสอบงบประมาณ preview for free. Reserve called from code (demo
  data, tests) still reserves the single code directly.
- **P3. ปรับถัวจ่าย after reserve.** The same dialog opens on the reserved slip.
- **D-window. A slip linked to a พ.1 has exactly two editable windows:**
  - draft, while the พ.1 is at รอจองงบประมาณ (`to_verify_budget`);
  - reserved and unused, while the พ.1 is at `to_approve` — reserved but not yet sent to
    e-Saraban. From `sent` on, the letter's budget table and its signers must all see one
    split; to change it, pull the letter back first.
  The windows are enforced server-side, not only in the view.
- **Standalone slips** (no พ.1, reserved by a Budget User) may use the split while
  **draft**. To change a reserved one, use กลับแบบร่าง, which already releases an
  unused reservation and keeps its number. Project and plan slips (they carry a Pool
  Tag) stay single-code; their grid is never shown.
- **D-acl (P4).** `group_purchase_request_budget_commit` gets write on
  `budget.commitment` and full access to `budget.commitment.split`, but **no create or
  unlink on the slip** — the slip is created server-side. Instead of a record rule, a
  write guard lets a user who is not a Budget User write **only the split**, and only
  on a slip whose พ.1 is in one of its windows. The reserve and re-cut themselves still
  run as sudo after the group and พ.1-state checks.

## Considered options

- **A ถัวจ่าย grid on the พ.1** — rejected (D1): the พ.1 would duplicate the slip, and
  every consumer of the slip would have to learn a second source.
- **A separate wizard** — rejected (D-form): users want to see the ใบจองงบประมาณ they
  are creating, and one form serves the standalone slip and the พ.1 alike.
- **Editing the reserve events directly** — impossible: events are immutable (ADR-0017).
- **The OWL reservation picker** (ADR-0006) — rejected: root ADR-0010 removed it from the
  พ.1, and a plain one2many grid needs no client code.
- **A record rule for the committer group** — rejected: group rules are OR-ed, so a rule
  on that group would also restrict Budget Users who hold it, unless every budget group
  got a matching `(1=1)` rule. The write guard also has to check the พ.1 state, which a
  rule cannot express cheaply.

## Consequences

- The header `account_id` is the writable Primary Code, not ADR-0006's computed mirror.
- The reservation info card on the พ.1 lists the ถัว codes. The พ.1 print, the e-Saraban
  letter and the dashboard still show only the Primary Code (follow-up).
- Existing slips have no split rows and behave exactly as before; no migration.
- A slip left in draft by a closed dialog stays linked to its พ.1 and is reused by the
  next Reserve; ดึงกลับ and ตีกลับ treat a draft slip as "nothing reserved".
