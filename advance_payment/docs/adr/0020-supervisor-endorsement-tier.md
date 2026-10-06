# Supervisor endorsement tier is reintroduced ahead of Verify/Approve

Status: accepted (amends ADR-0006; pre-production, no migration/version bump)

## Context & Decision

ADR-0006 dropped the whole Endorse → Approve chain — both the borrower's own first-line
supervisor and the org-routed Dean/ผอ.กองคลัง tier above `to_approve` — as unconfirmed
requirements, leaving `draft → to_verify` go straight from the borrower to the finance
officer's document check.

KMITL now confirms the **first tier only**: the borrower's own line manager
(`employee_id.parent_id`) must **endorse** (เห็นชอบ) the request before the finance officer's
Verify step. The org-routed Dean/ผอ.กองคลัง → Deputy Rector routing above `to_approve` stays
**deferred** — ADR-0006's reasoning against a placeholder `base_tier_validation` chain for that
tier is unaffected.

A new state, `to_endorse`, is inserted right after `draft`:

```
draft → to_endorse → to_verify → to_approve → approved → in_progress
      → reported → to_reconcile → done
(+ negative: cancel)
```

Two existing states are also renamed for clarity, independent of the endorsement work:
`waiting_transfer → approved` and `to_verify_report → reported`. `to_approve`'s label changes
to รอรองอธิการบดีอนุมัติ (naming the Deputy Rector as the approver); the state key itself is
unchanged. `to_endorse` is labelled รอผู้บังคับบัญชาเห็นชอบ, not …อนุมัติ: the glossary reserves อนุมัติ for
Approve, and with both steps reading อนุมัติ the statusbar would not tell them apart.

## Design

- **The endorser is suggested, not dictated.** `endorser_id` (`res.users`, `store=True`,
  **`readonly=False`**, `copy=False`, `tracking=True`) is a stored compute over
  `employee_id.parent_id.user_id` — a default that follows the borrower, which the form may
  override, because a request sometimes has to go to somebody *above* the direct manager. A
  plain `default=` would not do: the `user` tier may draft on behalf and `employee_id` stays
  editable in draft, so a default evaluated from the *creator* would name the wrong manager.
  Who may change it follows `loan_verifier_id` / `approver_id` exactly — anyone editing the
  draft, and a manager thereafter.
- **`employee_id` is the compute's only dependency**, and both omissions are deliberate. Not
  `employee_id.parent_id`: re-suggesting when the borrower changes is wanted, but an unrelated
  HR reorg must not silently overwrite a deliberate choice. Not `state` either: the value has to
  survive submit *and* a later ส่งกลับแก้ไข, and a compute cannot tell which dependency fired —
  keying on the borrower alone means a state change never reaches it. The `draft` guard inside
  then only covers an admin re-pointing `employee_id` on an in-flight request.
- **The borrower may not be their own endorser** (`_check_endorser_not_borrower`). Everything
  else is a matter of judgement, but self-endorsement would leave the step with no second pair
  of eyes at all — the same line `_check_submit_permission` draws for borrowing on behalf.
- **Reassigning a pending endorser re-points the To-Do.** `write()` re-runs
  `_schedule_workflow_activity('to_endorse')` whenever `endorser_id` changes on a record in
  `to_endorse`; without it the affordance is broken on arrival, leaving the task on somebody who
  can no longer act and the new endorser with nothing in their tray.
- **Endorse is distinct from Approve.** The glossary reserves อนุมัติ/"confirm" for Approve
  (`to_approve`); the new step is เห็นชอบ, state key `to_endorse` (follows the repo's `to_<verb>`
  convention), action `action_endorse`. `_check_endorse_permission` mirrors
  `_check_verify_permission`/`_check_approve_permission`: only `endorser_id` or an admin, and
  the step stamps its own `date_endorsed` next to the existing `date_submitted` /
  `date_verified` / `date_approved` — the chatter records the act too, but only a column is
  queryable for lead-time reporting. `action_reset_cancel_to_draft` clears it with its siblings.
- **Blocking exception at submit**, not a soft warning: a borrower with no manager, or whose
  manager has no linked `res.users`, cannot submit at all (`excep_missing_manager`, mirrors
  `excep_missing_bank_account`'s shape). Silently letting `endorser_id` come back empty would
  leave the To-Do with no assignee and the request stuck with nobody able to act on it. It tests
  `endorser_id` rather than the `employee_id.parent_id` chain, so a borrower whose `hr.employee`
  has no manager set can still name one by hand and proceed. The rule scopes itself to
  `state in ('draft', 'to_endorse')`: past the endorsement the endorser is already named on the
  record, so this must not false-block the loan officer's own corrections in `to_verify`.
- **Being named `endorser_id` always grants access**, whatever advance-payment tier the endorser
  holds — none included. The endorser is pickable, and a supervisor who never borrows would
  otherwise receive a To-Do (automated, so Odoo never checks the assignee can read the request)
  they could neither open nor endorse, stranding it in `to_endorse`. Hence
  `advance_payment_endorser_rule` on `base.group_user` (read/write — endorse writes state and
  posts) plus matching read/write ACL on `advance.payment` and read on the loan type and return
  line the form embeds. Group rules OR together, so it only widens access; return lines had no
  rule before, so an unrestricted own-only rule keeps every advance-payment tier as it was. The
  global OU rules (`advance_payment_operating_unit`, and `_access_all`'s rewrite of them) OR the
  endorser in too, since a global rule ANDs with everything. The branch is ANDed with
  `state != 'draft'`: the field is prefilled in draft and an unsubmitted draft must stay
  private. `endorser_id` is limited to internal users (`share = False`), whom the rule covers.
- **The endorser needs a menu of their own.** The tier is own-only, so neither สัญญาของฉัน (own
  records) nor สัญญาเงินยืมทั้งหมด (`group_advance_payment_user`) reaches the requests they must
  act on; without one the only route in is the To-Do activity. Hence the `รอฉันเห็นชอบ` filter
  (`endorser_id = uid` and `state = to_endorse`) plus its action and menu. Verify and Approve
  need no equivalent: both groups imply `group_advance_payment_user` and already see everything.
- **`action_endorse_reject`** (ส่งกลับแก้ไข) is endorser/admin-gated, `to_endorse → draft`, same
  shape as `action_reset_to_draft`. `action_recall` (the borrower's own pull-back) now also works
  from `to_endorse`.
- **`to_endorse` counts as active** for the one-active-agreement-per-borrower rule
  (`ACTIVE_STATES`) and as a material-fields-locked state (`READONLY_STATES`) — the request is
  already out of the borrower's hands the moment it is submitted. `loan_reason` is the one
  exception: it stays editable through `draft`, `to_endorse` and `to_verify` (`REASON_READONLY_STATES`
  does **not** add `to_endorse`), since the officer may still send it back for wording fixes
  without having touched the endorsement.
- **`advance_payment_check_exception`** guards `to_endorse` *and* `to_verify` — `to_endorse`
  because that is where `action_submit` now lands the record, `to_verify` because ADR-0005 lets
  the loan officer still correct `loan_amount` / `bank_id` / `reference` there, and those edits
  must face the same blocking rules the borrower's submit did. Guarding only the new state would
  have opened a hole the pre-ADR-0020 code did not have.

## Consequences

- No migration and no manifest version bump: the module is still pre-production. A UAT database
  needs a manual SQL fixup (or reinstall) to remap `waiting_transfer`/`to_verify_report` rows and
  backfill `endorser_id` — the initial compute only fills rows still in `draft`, every in-flight
  row keeps a NULL endorser by design.
- `data/advance_payment_exception_data.xml` is `noupdate="1"`, so a database that already
  installed an earlier cut of this branch keeps the first version of `excep_missing_manager`
  (unscoped domain, old name). Reinstall or fix that one rule by hand; a fresh install is fine.
- Every place that referenced `waiting_transfer` or `to_verify_report` by string had to be found
  and renamed — the model, both bridge modules (`advance_payment_followup`,
  `purchase_request_advance_payment`), and every view attrs/domain that listed them. There is no
  compatibility shim; the old state values simply no longer exist.
- `advance_payment_budget` (gates on `!= 'draft'` only), `advance_payment_operating_unit` (`draft`
  only) and `agx_approval_advance_payment` (`cancel`/`done`/`draft`/`in_progress` only) needed no
  changes — none of them name a renamed or inserted state directly.
