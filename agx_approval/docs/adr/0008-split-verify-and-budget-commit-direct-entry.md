# ADR-0008: Split verification from budget confirmation; budget code and dimensions entered directly

## Status

Accepted

## Context

A submitted request used to wait in a single step, `to_verify`
(รอตรวจสอบ / จองงบประมาณ). There, one budget officer
(`budget.group_budget_commitment`) both checked the request and reserved its
budget, picking the budget code and dimensions from the chart picker
(เลือกงบประมาณจากผังงบ). The institute wants checking the data and committing
the money to be two duties held by different people, and users found the
chart picker slower than choosing the values directly.

## Decision

- **A new state, `to_commit` (รอยืนยันงบประมาณ), sits between `to_verify`
  (now รอตรวจสอบข้อมูล) and `to_send`.**
  - `to_verify → to_commit` is ยืนยันตรวจสอบ (`action_confirm_verify`), held by
    `group_approval_verify`.
  - `to_commit → to_send` is ยืนยันงบประมาณ (`action_reserve_budget`, which
    reserves), held by `group_approval_budget_commit`.
  - Project mode lands in `approved` from `to_commit` (ADR-0005).
- **The two groups are separate and independent.**
  - Neither implies the other, and neither has a category, so each is its own
    checkbox. Both imply `group_approval_user`.
  - `budget_commit` also implies `budget.group_budget_commitment`, so it can
    create the ใบจอง.
  - No existing role is changed; admins grant the groups explicitly.
- **Each step's own role edits the budget code and dimensions while its step is
  open:** the verifier at `to_verify`, the confirmer at `to_commit`.
  - ยืนยันตรวจสอบ does not require them to be complete. Completeness and
    availability are enforced once, at ยืนยันงบประมาณ.
- **The chart-picker button is removed from the request form.**
  - รหัสงบประมาณ and the four dimensions are plain editable fields.
  - The code is limited to `_reservation_account_domain()`: the same
    non-procurement baseline and category pin the picker applied (ADR-0004).
  - Drawing an existing reservation (`reservation_commitment_id`, project mode)
    is unchanged.
- **Either role can ตีกลับ one step back, with a mandatory reason:**
  `to_commit → to_verify` or `to_verify → draft`.
- **On multi-product categories, `plan_amount` becomes the requester's Spending
  Ceiling.**
  - It is stored, and the line total must equal it: a blocking exception checked
    at every transition that runs `detect_exceptions`.

## Consequences

- **The requester no longer sees balances while choosing.** The picker's
  per-node available balance is no longer shown. Insufficient funds surface only
  when ยืนยันงบประมาณ is pressed, through `_check_budget_availability`.
- **This overrides budget ADR-0006's "the picker is the entry surface" for
  `approval.request` only.** Other hosts keep the picker. The mixin's
  `action_open_reservation_picker` remains available.
- **Downstream modules follow the new step:**
  - `agx_approval_budget_todo`'s จองงบประมาณ Todo now fires on `to_commit`.
  - `budget.group_budget_commitment` alone no longer shows the budget section on
    the request form.
