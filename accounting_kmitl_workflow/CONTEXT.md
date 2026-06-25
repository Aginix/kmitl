# Accounting Workflow

The two-step maker-checker approval that every `account.move` passes through before it is posted: a maker submits, a separate approver approves, and approval posts the entry.

## Language

**Maker** (ผู้จัดทำ/ผู้ตรวจสอบ):
The person who prepares and checks an entry — a single role covering both jobs. The maker performs **Submit**. Tracked in `submitted_by`. Belongs to `accounting_kmitl.group_accounting_kmitl_user`.
_Avoid_: Preparer alone, Reviewer alone (they are the same person here), Creator.

**Approver** (ผู้อนุมัติ):
The person who authorises an entry. The approver performs **Approve**, which posts the entry. Tracked in `approved_by`. Belongs to `accounting_kmitl.group_accounting_kmitl_manager`.
_Avoid_: Validator, Verifier, Poster.

**Submit**:
The maker's action that locks the entry (`state` → `submitted`), assigns its number, and requests approval (`workflow_state` → `to_approve`).
_Avoid_: Confirm, Send.

**Approve**:
The approver's action that posts the entry immediately. There is no separate Post step.
_Avoid_: Validate, Confirm, Post (Post is the side effect, not the action the user takes).

**Reject**:
The approver's action that sends an entry awaiting approval back to `draft` with a logged reason.
_Avoid_: Refuse, Decline, Cancel (Cancel is a different, terminal move state).

**Recall**:
The maker's action that withdraws an entry from approval back to `draft` (the "Reset to Draft" button while awaiting approval).
_Avoid_: Withdraw, Unsubmit, Revoke.

**`workflow_state`**:
The approval cycle state, kept separate from the move's real `state`: `none` → `to_approve` → `approved`/`rejected`. Distinct from `state` so the underlying accounting lifecycle (`draft`/`submitted`/`posted`/`cancel`) is untouched.
_Avoid_: approval_state, status (overloaded).

**`display_state`**:
The single user-facing status shown on the status bar, computed by merging `state` and `workflow_state`. The maker and approver read this; the real fields drive the buttons.
_Avoid_: status, state (the real one).

**System move**:
An `account.move` posted programmatically (payment counterparts, reversals, exchange differences, demo data). These bypass the workflow — the gate is enforced only on the manual Post button, never inside `_post()`/`action_post()`.
_Avoid_: Auto move, Technical move.
