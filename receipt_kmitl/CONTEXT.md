# Receipt KMITL

Cash receipting and central-posting workflow for KMITL: departments (cashiers)
issue cash receipts, bundle them into cash-deposit slips, and central finance
posts the accounting entries.

## Language

**Cash Receipt**:
A record of money received at a department counter (`kmitl.receipt`). Numbered
`RC/<FY>/nnnn` the moment it is created — there is no separate "confirm" step.
The per-fiscal-year sequence is `no_gap`, so a save rejected by validation
gives its number back instead of burning it.
Lifecycle: `draft` (รอนำส่ง / To Submit, still editable by the issuing department)
→ `submitted` (locked, once pulled into a remittance and submitted) →
`approved` → `done` (posted to accounting by central finance), plus `cancelled`.
_Avoid_: Invoice, bill, Confirm (old action, removed — receipts are numbered at
creation, not on a separate confirm step)

Cancelling a receipt still attached to a `draft` remittance (`action_cancel`)
automatically detaches it — clears `remittance_id` and removes it from the
remittance's `receipt_ids` in the same write, with a chatter note on both
records — rather than requiring a manual detach first.

**Receipt Remittance** (รายงานนำส่งคลัง):
The document a department submits to remit its confirmed receipts to the central
treasury (`kmitl.receipt.remittance`). Bundles many receipts (like an HR expense
sheet bundles expenses) — all confirmed receipts under its department **subtree**;
posting it (`posted`) creates each receipt's accounting entry. Numbered `RM/<FY>/nnnn`.
_Avoid_: Cash deposit, bank deposit (this is remittance to the treasury, not a
bank deposit), batch

**Removing a receipt** (นำใบเสร็จออกจากรายงาน):
Removing a single receipt from a `submitted` remittance via the standard o2m
widget (×) on `receipt_ids` so it returns to the pool of unremitted receipts —
the way an error on one receipt is corrected without tearing down the whole
remittance. **Reject** (whole-document, approver-only) is the way to send the
entire remittance back to `draft` with a reason.
_Avoid_: Detach (old term for a custom button that was never built)

**Issuing Department**:
The organizational unit that issued a receipt or owns a deposit — a `departments`
analytic account exposed on the header as `department_analytic_id`, a
`store=True, required=True` convenience field computed/inverted against
`analytic_distribution` (the `analytic.mixin` JSON field, the source of truth).
A **business dimension only**: it drives remittance bundling (a remittance
pulls its department's whole subtree) — **not** the receipt running number
(per-fiscal-year only, shared across departments) and **not** access control
(that is the Operating Unit's job).
_Avoid_: Cost center

**Department dimension**:
The `departments` analytic account carried on a **receipt line**, one of the
six financial dimensions (compute/inverse from `analytic_distribution`). Kept
in sync with the header's Issuing Department on every create/write — see
`kmitl.receipt._sync_analytic_to_lines`. The header is the single source of
truth: every save pushes it onto every line, so this column is `readonly`
in the form.

**Walk-in Customer**:
The default partner used on a receipt when no specific customer is named.
_Avoid_: Anonymous, cash customer

**Payment Type** (ประเภทการชำระเงิน):
The 3-way choice — cash / cheque / transfer — selected first on the receipt
header (`kmitl.receipt.payment_type`), before the specific `payment_method_id`
(which is domain-filtered to methods of that type). Cheque adds required
`cheque_number` + `cheque_date`; transfer adds required `transfer_date`;
switching type clears the other type's fields and the payment method.
_Avoid_: Other (removed as a payment type — every receipt is cash, cheque, or
transfer)

`payment_type` and `payment_method_id.payment_type` are enforced to match by
`_check_payment_method_matches_type` (an `@api.constrains`, not just the form's
domain) — the domain only guides UI selection and does nothing against
imports or API writes. The printed receipt ticks its box from, and the
summary report filters on, the receipt's own `payment_type` — not the
method's.

**Payment Method**:
A named way money was received (`kmitl.payment.method`) — cash / cheque /
transfer — carrying the debit GL account and journal used at posting. Filtered
on the receipt form by the header's Payment Type.

**Viewer / User / Manager**:
The three permission **tiers** (a single hierarchical dropdown; each implies the
one below). *Viewer* reads only. *User* (เจ้าหน้าที่หน่วยงาน) manages receipts and
remittances (create/confirm/submit) but cannot approve or post accounting.
*Manager* adds configuration (payment methods, walk-in, exception rules). All
three see the app; sub-menus differ by tier.
_Avoid_: Cashier (old term)

**Remittance Approver** (ผู้อนุมัติรายงานนำส่ง):
An **independent capability** (a checkbox, not a tier) added on top of a user,
group `group_receipt_kmitl_remittance_approver`: the one who may `approve` or
`reject` a `submitted` remittance and the one who may mark it `posted` —
creating the accounting entries — so it carries real accounting rights. Encodes
the department-vs-treasury segregation of duties (Manager holds it implicitly).
Who sees which remittance is governed by Operating Unit, not by this group.
_Avoid_: Treasury Officer, Central Finance (old terms)

**Operating Unit**:
The access-control boundary for receipts and deposits (`operating_unit_id`,
from the OCA `operating_unit` framework). Provided by the add-on module
`receipt_kmitl_operating_unit`; the base module carries no row-level scoping.
_Avoid_: Business unit, branch (unless referring to the partner branch code)
