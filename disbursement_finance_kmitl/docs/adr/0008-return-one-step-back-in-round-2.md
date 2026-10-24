# 0008 — Round 2 is returned one step back at a time, and the owner of a bill or voucher cancels it

- Status: **accepted**
- Date: 2026-10-22
- Supersedes: the "forward-only" rule in this module's `CONTEXT.md`

## Context

Round 2 was built forward-only: a request that was wrong at audit, authorization or
payment could only be cancelled and raised again, or have its bill reversed by
accounting. Round 1 already lets most steps send the request back with a reason
(`disbursement` return wizard), so the people in round 2 were the only ones with no
formal way to say "not yet" — they chased a manager for Reset to draft, which throws
away every signature, or had the request cancelled.

## Decision

Each round-2 step before the money leaves has its own return button, owned by that
step's group, going **one step back**: `bills_posted` → `approved`, `payment_audited` →
`bills_posted`, `payment_authorized` → `payment_audited`. It uses the same wizard as
round 1, with a mandatory reason on the chatter and a Todo to the group of the step it
returns to.

**The owner of a bill or voucher cancels it, not the return.** Returning from
`bills_posted` is refused while a bill that is not cancelled exists, and returning
from `payment_authorized` while such a voucher exists. A bill and a voucher are
accounting entries owned by the accounting and finance offices; a return that
reversed them on the returner's behalf would post to the GL under the wrong person's
authority. The same rule already stands in `disbursement_accounting_kmitl` for the
return to verification.

**The returned step's signature is archived**, and its who-did-it stamp
(`payment_auditor_id`, `payment_authorizer_id` and their dates) cleared, exactly as
round 1 does for a superseded verify or approval (`disbursement` ADR-0002). A request
that is audited again would otherwise print two auditors.

Returning from `payment_authorized` also **frees the payment lines** whose voucher was
cancelled. `_payable_payment_lines` skips a line that still points at a payment, so
without this authorizing again would raise no vouchers.

Not returnable: `paid` and `cleared`. The money has left; what is wrong from there is
corrected through the account.move maker-checker.

## Consequences

- The approver's Reject of round 1 is unchanged: it does not move `state`
  (`disbursement` ADR-0001).
- A request returned to `approved` goes back to `bills_posted` by itself when
  accounting posts its replacement bills (`account_move._post`); nothing else moves it.
- Entering `bills_posted` through a return notifies the auditors the way the first
  entry does, because that notification lives in `write`.
- The bills and vouchers a return waits on are checked as the returner sees them. A
  record rule that hides a bill from the returner would let the return through.
