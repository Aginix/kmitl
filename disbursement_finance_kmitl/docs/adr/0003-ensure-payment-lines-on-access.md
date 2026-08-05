# Payment lines are ensured on access, not created only at the state transition

Payment lines could have been created once, when the request enters
`bills_posted`. Instead `_ensure_payment_lines()` is idempotent — keyed on
(request, bill), it makes rows for posted bills that have none — and is called
from entering `bills_posted`, from the audit action, and from the Payment
Review opener. This costs nothing to call repeatedly and buys three things: a
request that somehow reached the payment phase can never show an empty payment
tab, a bill reversed and re-issued by accounting gets its row without anyone
intervening, and a database whose requests predate this model needs no
migration.

## Consequences

Creating records from a user-triggered action is a deliberate deviation from
keeping read paths free of writes. It is acceptable here because all three call
sites are buttons a person presses, never `read()` or a compute, so no write
happens while a form renders.

**If this causes trouble, this is the decision to revisit.** The failure modes
to watch for:

- Two officers opening the Payment Review at the same moment racing to create
  rows for the same bill — the (request, bill) key must be enforced by a
  database constraint, not only by the filter in the ensure method.
- A row appearing for a bill that accounting posted late, after the auditor had
  already reviewed and the authorizer had already signed — it carries the
  subject's defaults, which nobody audited. Today the same payee would be paid
  from the same un-reviewed defaults anyway (the old code re-derived them from
  the request lines at payment time), and the Payment Review now puts that row
  in front of the finance officer before the money moves, so this work narrows
  the hole rather than opening it. It does not close it: a forward-only
  workflow has no way to send such a row back for audit.
- Someone extending the ensure call to a compute or an `onchange` for
  convenience, at which point the read path is no longer clean and the
  reasoning above stops holding.

If any of these bite, move creation back to the single `bills_posted`
transition and accept that databases need a migration.
