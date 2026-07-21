# Two-approver step via a parallel `approval_state` (not tier.validation, not new `state` values)

The `verified → approved` transition on `disbursement.request` requires **two
approvals in sequence** — the Finance Division Director (ผอ.กองคลัง) then the
Rector-delegated approver (ผู้ได้รับมอบอำนาจอธิการบดี), on every request
regardless of amount, with the budget committed only on the second. This is
built as a **parallel `approval_state` field** on the request (`none →
pending_finance → pending_rector → approved`/`rejected`) with two group-gated
approve buttons, leaving the real `state` machine untouched.

Two alternatives were rejected:

- **OCA `base_tier_validation`** (as used by `advance_payment_tier_validation`)
  fits the "N approvers in sequence" shape exactly, but ships its own review
  widget **and its own systray/notification surface**. KMITL is consolidating
  all task notifications onto the `mail_activity_todo` notification center
  (systray + inbox + Discuss "Todos"); a second, parallel notification surface
  would compete with it. Expressing each pending approval as a native
  `mail.activity` execution Todo instead means the existing notification center
  surfaces it for free.
- **Adding real values to `state`** (e.g. `verified → finance_approved →
  approved`) would ripple through every consumer that keys off `state`: the
  accounting bridge's bill-creation gate (`state == 'approved'`), its
  `bills_posted` extension, the finance bridge's pipeline, and the
  return-to-verification guards. A parallel sub-field confines the change.

This mirrors `accounting_kmitl_workflow`, which added a parallel `workflow_state`
to `account.move` for the same reasons (its `display_state` compute comment even
notes it "mirrors `disbursement.request.display_status`").

## Consequences

- The "who approved when" audit that `tier.validation.review_ids` gives for free
  is built by hand as `finance_approver_id`/`finance_approve_date` and
  `rector_approver_id`/`rector_approve_date`, plus the `todo.log` snapshot each
  Todo leaves when cleared via `activity_feedback`.
- `action_approve` is **repurposed** as the second (Rector) step: it now requires
  `approval_state == 'pending_rector'` and is the single place the budget hook
  (`_action_approve_budget`) fires. Any code that called `action_approve()` on a
  merely-`verified` request must first go through `action_approve_finance()`.
- `display_status` gains `pending_finance` / `pending_rector` so the status bar
  shows the outstanding approval. The accounting bridge's `_compute_display_status`
  override had its `@api.depends` widened to include `approval_state`, otherwise
  the bar would not refresh between the two approvals when that bridge is installed.
- A post-migration moves in-flight `verified` requests to `pending_finance` so
  they are not stranded without an approve button after upgrade.
- Rejection reuses neither `state` nor the existing return flows: it sets
  `approval_state = 'rejected'` and keeps the request at `verified`, from which
  **Request Approval Again** restarts the cycle at the Finance Director.
