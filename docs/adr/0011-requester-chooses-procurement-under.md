# พ.1 จัดซื้อภายใต้: the requester names the โครงการ or แผนจัดซื้อจัดจ้าง on the พ.1 form

## Status

Accepted (2026-10-05). Supersedes budget
[ADR-0006](../../budget/docs/adr/0006-plan-driven-pr-created-from-plan.md) (a plan PR is
created from the plan). Amends budget
[ADR-0015](../../budget/docs/adr/0015-pr-draws-only-source-backed-reservations.md) (the
พ.1 picks the source's ใบจอง; its terminology note) and
[ADR-0010](0010-pr-split-verify-and-budget-commit-direct-entry.md) (who sets the
source).

## Context

- A พ.1 bought under a โครงการ/กิจกรรม or a แผนจัดซื้อจัดจ้าง is created only from that
  source's form: สร้างใบขอซื้อ on `kmitl.project`, สร้าง PR on `procurement.plan`
  (budget ADR-0006, ADR-0007). Most requesters never open those forms.
- The in-form source radio (แหล่งงบประมาณ) sits in the budget section that only
  ผู้ตรวจสอบ พ.1 and ผู้จองงบประมาณ พ.1 see (ADR-0010). It draws a project/plan by
  picking that source's ใบจองงบประมาณ, a slip number the requester has never seen.
- The requester is the person who knows whether the purchase is under a project or a
  plan, but cannot say so on the พ.1. This was logged as a deferred gap in `CONTEXT.md`.

## Decision

1. **The question is "จัดซื้อภายใต้", with three answers.** _งบประมาณปกติ (ไม่อยู่ภายใต้
   โครงการหรือแผน)_, _โครงการ/กิจกรรม_ or _แผนจัดซื้อจัดจ้าง_. The last two are followed
   by which project or plan. The term replaces แหล่งงบประมาณ on the พ.1, in the glossary
   and in the ADRs. คำขออนุมัติ keeps its own "วิธีเลือกงบประมาณ".
2. **The requester proposes and the verifier confirms.** The answer lives in one field
   per source (`kmitl_project_id`, `procurement_plan_id`), visible to the requester.
   There is no separate "proposed" field. Chatter tracking records who changed what.
3. **Only sources whose money is already reserved can be picked.** A project can be
   picked in `to_send`, `sent` or `in_progress`. A plan can be picked in `verified`. The
   list holds only the requester's own OUs, and only sources of the พ.1's ปีงบประมาณ.
   The existing global OU rules on both models do this, and PR users can already read
   both models.
4. **The fiscal year comes first and filters the sources; choosing a source fills and
   locks the budget code and all dimensions,** taken from the project/plan. The form
   asks ปีงบประมาณ, then จัดซื้อภายใต้, then which project/plan. Changing the year drops
   a source of another year. To correct the code or dimensions, change or clear the
   project/plan. Dimensions are never edited one by one.
5. **The requester picks the project/plan, not its ใบจอง.** The ใบจอง dropdown is gone
   for these answers. A project and a plan each hold exactly one live commitment, so the
   slip adds no information. At Reserve the พ.1 finds that commitment and re-takes the
   code, dimensions and fiscal year from it.
6. **The พ.1 can wait for an unsigned project.** ตรวจสอบ proceeds as normal. The พ.1
   then waits at `to_verify_budget`. Reserve refuses until the project is `in_progress`
   (the existing gate of kmitl_project ADR-0005), and the message names the project's
   current state. If the project is rejected, cancelled or returned, nothing happens
   automatically. People ตีกลับ, change the answer or ยกเลิก.
7. **A project's headroom counts a พ.1 only once it has drawn (at Reserve).** Before
   that, the headroom is shown on the พ.1 for information only. A draft, or a
   `cancelled` / `rejected` พ.1, never counts.
8. **A plan is claimed as soon as it is chosen (1 แผน = 1 พ.1).** While a live พ.1 holds
   a plan, it drops out of everyone else's dropdown. ยกเลิก, ปฏิเสธ or choosing another
   answer releases it, and `cancelled` releases it exactly like `rejected`. The plan
   moves to `in_progress` **at Reserve**, not when the พ.1 is created.
9. **Before Reserve, the owner of each step may change the answer:**

   - the requester at `draft`;
   - the verifier at `to_verify`;
   - the committer at `to_verify_budget`.

   **After Reserve the answer is locked**, and ดึงกลับ (Reset) does not reopen it.
   ADR-0015 still holds: moving a พ.1 to another source after Reserve means cancelling
   it and creating a new one.

10. **Both create-from-source buttons are removed** (project สร้างใบขอซื้อ, plan สร้าง
    PR). Every พ.1 starts on the พ.1 form. The smart buttons that list a source's พ.1
    stay.

## Considered options

- **Keep the create-from-source buttons and add the in-form choice.** Rejected. There
  would be two entry paths with different timing: the button links the commitment and
  starts the plan at create, the form waits for Reserve. Each rule would need to be
  written twice.
- **Let the requester propose into a separate field and have the verifier copy it.**
  Rejected. Two fields would have to stay in sync, and chatter tracking on the one field
  already shows who proposed and who changed it.
- **Let the requester pick the ใบจองงบประมาณ.** Rejected. The requester has never seen
  the slip number, and a project or plan holds exactly one live slip, so picking it adds
  nothing (ADR-0015 already calls a re-pick within the same source a no-op).
- **Offer only `in_progress` projects.** Rejected. Units prepare their purchases while
  the project's หนังสือ is still being signed. Gating at Reserve keeps the rule without
  blocking that preparation.
- **Count a project's headroom as soon as the project is chosen.** Rejected. Drafts that
  never go further would hold another unit's headroom.
- **Claim a plan only at Reserve, as with project headroom.** Rejected. Project money
  can be split between requests, so counting at draw is enough. A plan is realised by
  exactly one พ.1. If the claim waited for Reserve, a second requester would find out
  only after their พ.1 had been verified. The two sources therefore commit at different
  times **on purpose**.

## Consequences

- **The two create-from-source paths are gone.** Neither `kmitl.project` nor
  `procurement.plan` creates a พ.1 any more. Their `action_create_purchase_request` and
  `can_create_purchase_request` are removed.
- **`use_project` / `use_procurement_plan` stay as discriminators.** They are now set
  when the answer is chosen. The purchase order, the make-PO wizard,
  `purchase.request.approval` and the over-budget exception rule still read
  `use_procurement_plan` (budget ADR-0006's reasoning for keeping it still holds).
- **The budget-edit lock now depends on whether the พ.1 has drawn, not on those flags.**
  The flags are set from the first choice, but the choice stays open to each step's
  owner until Reserve.
- **A plan's `in_progress` now means "a พ.1 has drawn its money".** It no longer means
  "a พ.1 exists". A chosen but undrawn plan stays `verified` and is claimed. The claim
  is a property of the พ.1 link, not a plan state.
- **A พ.1 waiting on an unsigned project sits in the committer's queue at
  `to_verify_budget`** even though Reserve will refuse. This is accepted: the refusal
  message says which project state it is waiting for.
- **ADR-0015's rules carry over to the new field.** The project/plan dropdown is now
  where source eligibility is enforced, instead of the ใบจอง picker. The regulatory
  server gate (`_check_drawable_commitment`) is unchanged and still runs at Reserve.
  ADR-0015's "Reset does not reopen the source" is kept for the period after Reserve.
  Before Reserve the answer is deliberately open.
- **The mode is the answer, the project/plan only its detail.** The mode is never
  inferred from a picked project/plan: any other mode drops it, and a copy keeps the
  mode (a plan copy then needs a new plan, 1 แผน = 1 พ.1).
- **UAT data needs no migration.** A พ.1 made with the old buttons already carries its
  commitment, and its plan is already `in_progress`. Reserve must accept that state for
  the plan's own holder.
- **Terminology.** "จัดซื้อภายใต้" replaces "แหล่งงบประมาณ", which sat too close to
  แหล่งเงิน (the `sources` dimension) and asked "where does the money come from" when
  the real question is "what is this purchase under". The normal answer is worded
  _งบประมาณปกติ_ rather than _ผังงบประมาณ_: the requester does not pick from the chart,
  the verifier enters the code.
