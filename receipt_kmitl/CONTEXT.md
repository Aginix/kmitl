# Receipt KMITL

Cash receipting and central-posting workflow for KMITL: departments (cashiers)
issue cash receipts, bundle them into cash-deposit slips, and central finance
posts the accounting entries.

## Language

**Cash Receipt**:
A record of money received at a department counter (`kmitl.receipt`). Issued
(confirmed) by a cashier, printed, then posted to accounting by central finance.
_Avoid_: Invoice, bill

**Receipt Remittance** (รายงานนำส่งคลัง):
The document a department submits to remit its confirmed receipts to the central
treasury (`kmitl.receipt.remittance`). Bundles many receipts (like an HR expense
sheet bundles expenses) — all confirmed receipts under its department **subtree**;
posting it (`done`) creates each receipt's accounting entry. Numbered `RM/<FY>/nnnn`.
_Avoid_: Cash deposit, bank deposit (this is remittance to the treasury, not a
bank deposit), batch

**Detach** (ถอนใบเสร็จออกจากรายงาน):
Removing a single receipt from a submitted remittance so it returns to the pool
of unremitted confirmed receipts — the way an error on one receipt is corrected
without tearing down the whole remittance. A submitted remittance is never reset
as a whole (only cancelled, which releases all its receipts).
_Avoid_: Reject, return, reset

**Issuing Department**:
The organizational unit that issued a receipt or owns a deposit — a `departments`
analytic account stored on the header as `department_analytic_id` (a plain
required Many2one, kept as the source of truth). A **business dimension only**:
it drives the per-department fiscal-year running number and remittance bundling —
**not** access control (that is the Operating Unit's job).
_Avoid_: Cost center

**Department dimension**:
The `departments` analytic account carried on a **receipt line** as one of the
six financial dimensions (compute/inverse from `analytic_distribution`). Distinct
from the header Issuing Department, though usually the same value.

**Walk-in Customer**:
The default partner used on a receipt when no specific customer is named.
_Avoid_: Anonymous, cash customer

**Payment Method**:
A named way money was received (`kmitl.payment.method`) — cash / cheque /
transfer / other — carrying the debit GL account and journal used at posting.

**Viewer / User / Manager**:
The three permission **tiers** (a single hierarchical dropdown; each implies the
one below). *Viewer* reads only. *User* (เจ้าหน้าที่หน่วยงาน) manages receipts and
remittances (create/confirm/submit/detach) but cannot post accounting. *Manager*
adds configuration (payment methods, walk-in, exception rules). All three see the
app; sub-menus differ by tier.
_Avoid_: Cashier (old term)

**Treasury Officer** (เจ้าหน้าที่กองคลัง):
An **independent capability** (a checkbox, not a tier) added on top of a user:
the only one who may mark a remittance `done` — creating the accounting entries —
so it carries real accounting rights. Encodes the department-vs-treasury
segregation of duties (Manager holds it implicitly). Who sees which remittance is
governed by Operating Unit, not by this group.
_Avoid_: Central Finance (old term)

**Operating Unit**:
The access-control boundary for receipts and deposits (`operating_unit_id`,
from the OCA `operating_unit` framework). Provided by the add-on module
`receipt_kmitl_operating_unit`; the base module carries no row-level scoping.
_Avoid_: Business unit, branch (unless referring to the partner branch code)
