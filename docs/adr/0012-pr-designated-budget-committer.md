# พ.1 names one ผู้ยืนยันงบประมาณ (Designated Budget Committer) who gets the reserve Todo

## Status

Accepted. Changes how [ADR-0010](0010-pr-split-verify-and-budget-commit-direct-entry.md)
routes the reserve Todo; the rest of ADR-0010 is unchanged.

## Context

ADR-0010 routes the พ.1's reserve Todo to the whole role จองงบประมาณ พ.1 ∩ OU
(`purchase_request_budget_todo.automation_pr_draft_to_verify`). Everyone in that role gets a
Todo for every request, and no one knows which requests are theirs. This is the problem that
[ADR-0011](0011-pr-assigned-to-is-designated-verifier.md) solved for the verify step.

## Decision

- **A new field, `budget_verifier_id` (ผู้ยืนยันงบประมาณ), names the one ผู้จองงบประมาณ พ.1.**
  It lives in two new modules, `purchase_request_budget_verifier` and the auto-installing
  `purchase_request_budget_verifier_operating_unit`. No existing module is edited.
- **When it must be set**:
  - it can be filled from `draft`;
  - it is required when ตรวจสอบ is pressed (`to_verify → to_verify_budget`), because the ธุรการ
    knows the budget officer and the requester may not;
  - it cannot be cleared while the PR is at `to_verify_budget`;
  - it is editable until the PR ends.
- **Candidates**: members of `group_purchase_request_budget_commit`, and in the OU layer only
  those in the PR's OU. As in ADR-0011, one hook, `_get_budget_verifier_candidates()`, feeds
  the domain, the constraint and the onchange.
- **A personal Todo replaces the role broadcast.** Installing the module deactivates
  `automation_pr_draft_to_verify`, and uninstalling reactivates it. The Todo reuses the
  existing จองงบประมาณ activity type.
- **The Todo follows the state, as in ADR-0011:**
  - entering `to_verify_budget` schedules it;
  - leaving `to_verify_budget` marks it done only when the named person moved the PR to
    `to_approve`, and withdraws it otherwise;
  - reassigning at `to_verify_budget` moves it to the new person.
- **The ADR-0010 gate is unchanged**: any member of the group may still Reserve or ตีกลับ.

## Considered options

- **Reuse a field the PR already has**: there isn't one. `assigned_to` is the Designated
  Verifier (ADR-0011), and `budget_committed_by` records who actually reserved.
- **Keep the role broadcast alongside the personal Todo**: rejected. Everyone in the role
  would still get a Todo for every request, which is the noise this ADR removes.
- **Only the named person may reserve**: rejected for the same reason as in ADR-0011.
  Covering for an absent colleague must stay possible.
- **Edit `purchase_request_budget_todo`'s noupdate automation**: rejected. It would need a
  migration in a module that is already deployed, and switching the automation off from the
  new module can be reversed on uninstall.

## Consequences

- PRs already at `to_verify_budget` at install keep their role Todo. The remaining
  `purchase_request_budget_todo` automations still close it.
- Re-reserving at `to_approve` after a commitment is cancelled sends no Todo. This is
  unchanged from before.
- `agx_approval` uses the word ผู้ยืนยันงบประมาณ for its whole Budget Confirmer group.
  On the พ.1 it means the one named person.
