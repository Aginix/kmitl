# Data lives in the bridge, verbs live in the station

A station needs a document built — a vendor bill, a payment voucher — and the
model that document is linked to the request through already exists in a bridge
module (`disbursement_accounting_kmitl`, `disbursement_finance_kmitl`). The two
could be kept together, in either module. We split them.

## Decision

- **The bridge owns the data**: the link columns (`account.move.disbursement_request_id`),
  the one2many back (`bill_ids`), the derived lookups (`_related_move_domain`).
- **The station owns every verb**: `_create_bill`, `_prepare_bill_vals`,
  `_prepare_bill_line_vals`, the button, the guard, and the completion hook.
- **A module that extends a verb depends on the station**, not on the bridge.

The cut is what uninstalling costs. Uninstalling drops the module's columns and
models — so a column that outlives its station must not belong to it, or every
historical bill silently loses which request it paid. A *method* dropped on
uninstall costs nothing: the station is gone, so nobody can call it.

## Considered options

- **Everything in the bridge (rejected)** — the station would shrink to a button,
  and "which document does this station produce" would be answered two modules
  away from the station that produces it.
- **Everything in the station (rejected)** — the link column would go with it, so
  uninstalling the billing station would detach every bill ever raised.

## Consequences

- `disbursement_cash_revenue_handover`, which overrides `_create_bill()`, moves its
  dependency from `disbursement_accounting_kmitl` to `disbursement_wst_bill`. That
  is the honest shape: there is no handover to draw if there is no billing station,
  and Odoo will uninstall it along with the station rather than leaving a `super()`
  call with nothing underneath it.
- A bridge never names a station. It raises an event in its own vocabulary
  (`_on_bills_posted`) and the station listens.
