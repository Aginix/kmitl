# พ.1 `assigned_to` is the Designated Verifier (ผู้ยืนยันตรวจสอบ); supersedes ADR-0001 for the PR

## Status

Accepted — supersedes [ADR-0001](0001-assigned-officer-model.md) for `purchase.request`.

## Context

At `to_verify`, every member of `group_purchase_request_verify` in the OU can see a
submitted พ.1 ([ADR-0010](0010-pr-split-verify-and-budget-commit-direct-entry.md)), but no
one is told it is theirs. Requesters want to name the ธุรการ who should check their
request, and that person should get a Todo.

ADR-0001 repurposed the PR's OCA `assigned_to` as the **Assigned Officer** (เจ้าหน้าที่พัสดุ).
Its implementation, `procurement_assignment_kmitl`, was removed (37cbc548). The field is
now dormant on the PR and holds no data in production.

## Decision

- The PR's `assigned_to` now means **ผู้ยืนยันตรวจสอบ (Designated Verifier)**, via two new
  modules: `purchase_request_verifier` and the auto-installing
  `purchase_request_verifier_operating_unit`. The PA's own `assigned_to` (Approver) is
  untouched.
- **Candidates**: Verifier-group users, and in the OU layer only those in the PR's
  Operating Unit. One compute hook, `_compute_verifier_candidate_ids`, feeds:
  - the field domain;
  - an `@api.constrains`;
  - an onchange that clears a non-candidate and auto-picks a lone candidate.
- **Rules for the field**:
  - required to submit;
  - cannot be cleared while the PR is at `to_verify`;
  - editable until the PR ends (done/rejected/cancelled).
- **The ADR-0010 gate is unchanged**: any Verifier may still press ตรวจสอบ or ตีกลับ.
  Naming someone routes the Todo; it does not restrict who acts.
- **The Todo lifecycle is driven by state, not by buttons.** `write()` compares the state
  and assignee before and after:
  - entering `to_verify` by any path schedules the Todo;
  - leaving `to_verify` marks it done only when the Designated Verifier moved the PR
    forward (not draft/cancelled), and withdraws it otherwise;
  - reassigning at `to_verify` moves the activity to the new person.
- **Verifier ตีกลับ to draft** sends Execution Todos to `requested_by` and `create_uid`,
  deduplicated, with the reason as the note. On resubmit, the presser's Todo is done and
  the other is withdrawn. Cancelling withdraws both.

## Considered options

- **A new `verifier_id` field**: clearer name, but it leaves `assigned_to` dead on the PR
  for a third time and adds yet another user field next to `user_id`, `requested_by` and
  `verified_by`. Rejected: `assigned_to` already carries OCA's "Assigned to me" filter,
  tracking and follower subscription.
- **Hooking the buttons (`button_to_verify`, `button_to_approve`, …)**: rejected.
  `purchase_request_budget.button_to_approve` writes `to_verify_budget` itself and calls
  super only for the other records. The budget step's ตีกลับ and ดึงกลับ also write
  `to_verify` directly. A button wrapper would miss these paths; a state diff in `write()`
  catches every one.
- **Only the Designated Verifier may verify**: rejected. Covering for an absent colleague
  would need a rename first, and ADR-0010's group gate is the agreed authority.

## Consequences

- The PR's `assigned_to` and the PA's `assigned_to` now mean different things (Designated
  Verifier vs Approver). The Assigned Officer concept has no home on the PR. If it returns,
  it needs a new field.
- PRs already at `to_verify` when the modules are installed have no Designated Verifier and
  get no Todo until they pass through `to_verify` again.
- Notifying the requester when a PR is cancelled at `to_verify` is out of scope.
