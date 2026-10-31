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
  code, the **Primary Code** (รหัสหลัก). Its dimensions and code are first entered on
  the พ.1, by the verifier and then the budget committer (root ADR-0010 is unchanged
  there); the dialog may then change them (D-edit), and the พ.1 follows the slip.
- **D6. The `cross_chargeable` flag governs eligibility** (ADR-0006 stands). A ถัว code
  must be flagged, budgetable, an expense code, and funded at the slip's dimensions
  (Available > 0). The Primary Code must be flagged too once there is more than one
  code. Admins tick the flag on the budget account form and list, and through
  `budget_account_mass_edit`.
- **P1. The form gets a รายการจองงบประมาณ grid**, backed by a new
  `budget.commitment.split` (the **Reservation Split**). Row ★ is the Primary Code; its
  amount is **computed** as วงเงิน − Σ ถัว rows and read-only (D-remainder), so the
  total always equals the วงเงิน. The remainder may be **0** (the whole วงเงิน on ถัว
  codes; it then posts no reserve event) but never negative. Each row shows งบที่จองได้ and a sufficiency mark,
  and a banner names every row that is short. Each row also computes its code's จองเงิน / ผูกพัน / เบิกจ่าย / คงเหลือ from the
  ledger; the grid hides those columns (2026-10-28) and the slip's Budget Summary
  shows the totals.
  - จองงบ derives one reserve event per row, primary first, so ADR-0018's liquidation
    order is the split's order. A slip with no split rows reserves from its header
    exactly as before.
  - Re-cutting a reserved split cancels the reserve events and posts new ones, after
    re-checking every pool with the slip's own reservation given back. It is allowed
    only while nothing has been obligated, consumed or returned.
- **P2. Reserve on a พ.1 opens the same form as a dialog** (D-form). The button creates
  — or refreshes, when one was left behind — a **draft** slip from the พ.1: ปีงบ,
  dimensions, Primary Code and วงเงิน = the พ.1 total. The วงเงิน and ปีงบ are locked;
  the code and dimensions are editable (D-edit). ยืนยันจองงบประมาณ
  reserves every row at once and advances the พ.1; ปิด leaves a harmless draft (a draft
  locks no budget). The single-code case is the same dialog with one row, which gives
  ADR-0010's planned ตรวจสอบงบประมาณ preview for free. Reserve called from code (demo
  data, tests) still reserves the single code directly.
- **P3. ปรับถัวจ่าย after reserve.** The same dialog opens on the reserved slip.
- **ยกเลิกการจองงบ.** In the same window as ปรับถัวจ่าย (reserved, unused, not yet sent),
  the budget committer may cancel the reservation from the พ.1: the slip is cancelled
  (its money released) and the พ.1 steps back to รอยืนยันงบประมาณ, where the Primary
  Code and dimensions are editable again. The next Reserve revives the same slip, number
  and ถัว rows included. Without it, changing the Primary Code after reserving needs a ดึงกลับ to draft by
  the PR manager, because the slip form has no Cancel and an open พ.1 blocks
  กลับแบบร่าง on its slip.
- **D-edit (2026-10-31). The Primary Code and the four dimensions are editable in the
  dialog, in the same windows as the split.** Saving a reserved slip re-cuts it in one
  step, like ปรับถัวจ่าย: its reserve events are cancelled, every pool at the new
  coordinate is checked with the slip's own money given back, and the new events are
  posted. When the new code or dimension has no money the save is refused and the slip
  keeps its reservation untouched; nothing is released in between, unlike a
  reset-to-draft (budget.transfer). The พ.1's code, dimensions, line dimensions and
  product are copied from the slip. Typical use: after ตรวจสอบ, switch to another
  ส่วนงาน's budget without giving up the reservation first. A new Primary Code that is
  already a ถัว row merges into row ★; the old Primary Code is not kept as a ถัว row.
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
  write guard lets a user who is not a Budget User write **only the split, the Primary
  Code and the dimensions** (never the วงเงิน), and only
  on a slip whose พ.1 is in one of its windows. The reserve and re-cut themselves still
  run as sudo after the group and พ.1-state checks.

- **Packaging: ถัวจ่าย is an add-on, not core.** `budget_commitment_cross_charge` (depends
  `budget`) owns the Reservation Split, its grid, the re-cut and the account-form flag;
  `purchase_request_budget_cross_charge` (auto-installs with `purchase_request_budget`)
  owns the พ.1 dialog, ปรับถัวจ่าย, the edit windows and the committer's write access.
  Core keeps only two seams: `_check_reserve_availability(amounts=…)` and
  `_create_reserve_line_from_header` (overridden to post one event per row); the พ.1
  keeps `_reserve_new_budget` and ยกเลิกการจองงบ, which is useful without ถัวจ่าย.
  Without the add-ons, Reserve works exactly as before.

- **No category scope (re-confirmed 2026-10-28).** Any two flagged codes may be pooled,
  even across groups (e.g. ค่าไฟฟ้า with ค่าจ้างเหมาบริการ), because the regulation is
  not settled yet. Ticking a parent code has no effect; it is only a convenience for
  Mass Edit. If the regulation later limits ถัวจ่าย to groups, the planned shape is an
  explicit "กลุ่มถัวจ่าย" mark on a parent code, with flagged codes pooling only under
  the same group.

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
