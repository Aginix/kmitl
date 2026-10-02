# พ.1 budget step: verify and budget-commit are two duties; budget code and dimensions entered directly

## Status

Accepted

## Context

After [ADR-0008](0008-pr-clerk-step-and-owned-states.md), a พ.1 walks
`draft → to_verify (ธุรการตรวจ) → to_verify_budget (รอจองงบประมาณ) → to_approve`. In
practice the two steps were not two duties:

- `group_purchase_request_verify` sat in the hidden category and implied nothing, so
  only `base.group_erp_manager` held it. It gated the ตรวจสอบ button in the view and
  nothing else.
- The budget section, the Reserve button and the budget-edit rule all keyed on the
  generic `budget.group_budget_commitment` (role จองงบประมาณ). The same people therefore
  reserved พ.1 **and** คำขออนุมัติ.
- รหัสงบประมาณ and the dimensions were read-only and filled only through the chart
  picker (เลือกงบประมาณจากผังงบ).

`agx_approval` has already split checking the data from committing the money
(agx_approval ADR-0008). The institute wants พ.1 to work the same way.

## Decision

- **The two steps are held by two independent groups, neither implying the other:**
  - **ผู้ตรวจสอบ พ.1**: the existing
    `purchase_request_kmitl.group_purchase_request_verify` becomes a category-less
    checkbox implying PR User: All Documents (both duties work other people's requests;
    visibility stays OU-scoped). It presses ตรวจสอบ (`to_verify → to_verify_budget`).
  - **ผู้จองงบประมาณ พ.1**: the new
    `purchase_request_budget.group_purchase_request_budget_commit`, category-less,
    implying PR User: All Documents and `budget.group_budget_commitment`. It presses
    Reserve (`to_verify_budget → to_approve`).
  - Both are checked in Python, not only in the view.
- **`budget.group_budget_commitment` alone no longer reserves a พ.1.** The generic role
  จองงบประมาณ is unchanged and still serves คำขออนุมัติ. A new role **จองงบประมาณ พ.1**
  (`purchase_request_budget_todo`) grants the new group, and the reserve Todo is routed
  to it (∩ OU).
- **Each step's own group edits the budget code and dimensions while its step is open:**
  - the verifier at `to_verify`;
  - the budget committer at `to_verify_budget`, and at `to_approve` when the commitment
    was cancelled.
  - ตรวจสอบ does not require them to be complete. Completeness and availability are
    enforced once, at Reserve.
- **The chart-picker button is removed from the พ.1 form.** รหัสงบประมาณ and the four
  dimensions are plain editable fields. The code is limited to
  `_reservation_account_domain()`, the same domain the picker applied. Choosing a
  แหล่งงบประมาณ (โครงการ / แผนจัดซื้อจัดจ้าง) is unchanged.
- **ตีกลับ goes back one step, with a mandatory reason:**
  - `to_verify_budget → to_verify` by the budget committer, leaving any live commitment
    untouched;
  - `to_verify → draft` by the verifier.
  - This replaces the old Return, which sent both steps straight to draft.
- **Reserve runs under `sudo()` after the group check.**
  `budget.group_budget_commitment` carries no ACL on `budget.commitment`, so the
  reserve-new path would otherwise demand Budget User, which opens the whole budget app.

## Considered options

- **Keep `budget.group_budget_commitment` as the gate and add the new group beside it**:
  rejected. The new group would then grant nothing that the generic role does not, and
  the duty would not be PR-specific.
- **Make the budget committer the only one who enters the code**: rejected. The ธุรการ
  knows the request best, and the committer would have to send it back for every missing
  field.

## Consequences

- **The requester and the verifier no longer see balances while choosing.** Insufficient
  funds surface only when Reserve is pressed. A separate ตรวจสอบงบประมาณ (availability
  preview) button is planned to fill this gap.
- **This overrides budget ADR-0006's "the picker is the entry surface" for
  `purchase.request`.** The mixin's `action_open_reservation_picker` stays available to
  other hosts.
- **Admins must grant the new groups or role explicitly.** Existing holders of
  จองงบประมาณ lose the พ.1 Reserve button on upgrade. No users are seeded.
- **`purchase_request_budget_todo` re-routes its noupdate automation** through a
  migration to the new role.
- **The same ACL gap exists on `agx_approval`'s ยืนยันงบประมาณ** and is not fixed here.
