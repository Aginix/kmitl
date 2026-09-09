# Accounting Workflow

The two-step maker-checker approval that every `account.move` passes through before it is posted: a maker submits, a separate approver approves, and approval posts the entry.

The account move voucher PDF (`_kmitl_voucher_lines()`) prints debit rows before credit rows, stable within each side.

## Language

**Maker** (ผู้จัดทำ/ผู้ตรวจสอบ):
The person who prepares and checks an entry — a single role covering both jobs. The maker performs **Submit**. Tracked in `submitted_by`. Belongs to `accounting_kmitl.group_accounting_kmitl_user`.
_Avoid_: Preparer alone, Reviewer alone (they are the same person here), Creator.

An entry an accounting person typed may be submitted only by whoever created it — you do not submit a colleague's work. A **payment voucher handed over by the finance office** has no accounting author at all: another office prepared the money side and is done with it. Its maker is therefore **whichever accounting person picks it up to book**, and the creator rule does not apply to it — there is no colleague's work to take over. (Designed, not yet built — see `disbursement_finance_kmitl` ADR-0005.)

**Approver** (ผู้อนุมัติ):
The person who authorises an entry. The approver performs **Approve**, which posts the entry. Tracked in `approved_by`. Belongs to `accounting_kmitl.group_accounting_kmitl_manager`.
_Avoid_: Validator, Verifier, Poster.

**Submit**:
The maker's action that locks the entry (`state` → `submitted`) and assigns its number. On a journal entry it also requests approval (`workflow_state` → `to_approve`) in the same breath, because a locked entry is ready to post.

On a **payment** the two come apart: locking is what lets the finance office put the payment in an e-payment file, and the money has to reach the payee before the entry may be posted at all. A payment is therefore submitted by finance and requests approval only later, at its own **Hand-over** (see `disbursement_finance_kmitl/CONTEXT.md`). Read `submitted` as "locked and numbered", never as "waiting for the approver" — that is what `workflow_state` says.
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
