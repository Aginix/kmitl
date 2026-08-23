# Payment lines are ensured at every door, not only at the state transition

Payment lines could have been created once, when the request enters `bills_posted`.
Instead `_ensure_payment_lines()` is idempotent — keyed on the bill, it makes rows for
posted bills that have none — and is called from entering `bills_posted`, from the audit
action, from the Payment Review opener and from payment creation. This costs nothing to
call repeatedly and buys two things: a request that somehow reached the payment phase
can never show an empty payment tab, and a bill that accounting reversed and re-issued
gets its row without anyone intervening.

Two officers opening the Payment Review at the same moment would race to create rows for
the same bill, so the key is enforced by a database constraint (`unique(bill_id)`)
rather than only by the filter in the ensure method.

## Consequences

Creating records from a user-triggered action is a deliberate deviation from keeping
read paths free of writes. It is acceptable here because every call site is a button a
person presses, never `read()` or a compute, so no write happens while a form renders.

**If this causes trouble, this is the decision to revisit.** The failure modes to watch
for:

- A row appearing for a bill that accounting posted late, after the auditor had already
  reviewed and the authorizer had already signed — it carries the subject's derived
  paying account, which nobody audited. The Payment Review puts that row in front of the
  finance officer before the money moves, so this narrows the hole rather than opening
  it. It does not close it: a forward-only workflow has no way to send such a row back
  for audit.
- Someone extending the ensure call to a compute or an `onchange` for convenience, at
  which point the read path is no longer clean and the reasoning above stops holding.

If either bites, move creation back to the single `bills_posted` transition.
