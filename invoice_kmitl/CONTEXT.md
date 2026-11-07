# Invoice KMITL

Departments issue invoices to their debtors and collect on them. A department finance
officer issues an **ใบแจ้งหนี้** and hands the batch to the treasury office (กองคลัง),
who accepts it and sends it on to the accounting office (ห้องบัญชี) to book the
receivable. When the debtor pays, the department receipts the money straight from the
invoice, and the books settle the debt against that receipt. Before this module the
whole chain was paper: the treasury office issued every invoice itself, kept the debtor
register outside the system and reported twice to the accounting office.

## Language

**ใบแจ้งหนี้ / Invoice** (`kmitl.invoice`):
The document a department issues to a debtor to ask for money. Numbered
`IV/<FY>/nnnn` the moment it is created, because the department must have a paper to
hand the debtor before the accounting office has booked anything. The per-fiscal-year
sequence is `no_gap`. Every invoice carries a **วันครบกำหนดชำระ** (`date_due`) and all
four of the dimensions that matter to accounting — see ADR-0004. One customer, no
walk-in, one currency, no VAT. Full payment only: a part payment is not modelled.
Lifecycle: `draft` (the department edits it, or cancels it) → `submitted` → `accepted`
(locked, driven by its **รายงานนำส่งใบแจ้งหนี้**) → `issued` (the ใบตั้งหนี้ exists as a
draft, awaiting accounting) → `paid` (a receipt exists), plus `cancelled`.
_Avoid_: ใบตั้งหนี้, ใบวางบิล, ใบเสร็จ

**ใบตั้งหนี้ / AR invoice**:
The `account.move` of type `out_invoice`, on the journal ใบสำคัญลูกหนี้, that is the
accounting shadow of an invoice — the term `finance_kmitl_reports` already uses. 1:1
with the invoice but a different document: the invoice is the department's, the ใบตั้งหนี้
is the accounting office's, with another owner, another number and another moment of
birth. Raised as a draft when the submission is sent to accounting, then submitted and
approved like any other entry. Cancelling an issued invoice that accounting has already
posted reverses it with a draft **ใบลดหนี้** (`out_refund`), which the accounting office
finds under บัญชี ▸ ลูกหนี้ ▸ ใบลดหนี้ and submits and approves in turn.
_Avoid_: writing the invoice's number into `account.move.name` — that would corrupt the
AR journal's running number. The two are tied by `out_invoice.ref = invoice.name` and by
`account.move.kmitl_invoice_id`.

**เลขสองชุดต่อหนึ่งเหตุการณ์ / Two numbers for one event**:
`IV/<FY>/nnnn` is the number the debtor holds, issued at creation. `AR/<year>/nnnn` is the
accounting office's, issued when it submits the ใบตั้งหนี้. They never replace one another.

**รายงานนำส่งใบแจ้งหนี้ / Invoice Submission** (`kmitl.invoice.submission`):
The document a department uses to hand its invoices to the treasury office as a batch,
and the treasury office uses to pass them on to accounting. Numbered `IS/<FY>/nnnn` when
submitted. Pulls the draft invoices of its department **subtree**. Lifecycle: `draft` →
`submitted` → `accepted` (the treasury office has checked the batch) → `done` (sent to
accounting: one draft ใบตั้งหนี้ per invoice), plus `cancelled`. The same three-stage
shape as a Receipt Remittance, but it moves **documents**, not money.
_Avoid_: รายงานนำส่งคลัง (`kmitl.receipt.remittance` — that one sends **cash** to the
treasury), ใบปะหน้า, batch

**ทะเบียนคุมลูกหนี้ / Debtor register**:
Not a model: a list and pivot view over the invoices (`finance_kmitl` ADR-0008, a
worklist is a list view). It shows an invoice from the day it is a draft, with both
statuses side by side so that the stretch where money is on its way is visible.
_Avoid_: ลูกหนี้ on its own, which in this repository usually means the borrower of an
employee advance (`advance.payment`)

**ชำระแล้วของหน่วยงาน vs ชำระแล้วทางบัญชี / Paid for the department vs paid in the books**:
`kmitl.invoice.state = 'paid'` means the department took the money and issued the receipt.
`move_id.payment_state` (the **Accounting Payment Status** on the form) means the books have
settled the receivable. They differ while the receipt travels to treasury and on to
accounting, and that gap is **normal** — see ADR-0003.

**ใบเสร็จตัดหนี้ / Debt-settling receipt**:
A `kmitl.receipt` raised from an invoice (`invoice_id` set). Everything about it is an
ordinary receipt's except one leg: its entry credits the customer's receivable account
instead of revenue — see ADR-0002 and `receipt_kmitl`. Created by **รับชำระเงิน** (Receive
Payment) as a draft, for the invoice's full amount.

**ใบล้างลูกหนี้ / Receivable clearing entry**:
The entry of a debt-settling receipt, listed under บัญชี ▸ ลูกหนี้ the way ใบล้างเจ้าหนี้ lists
the payable side's.

**Submission Approver (กองคลัง) / User / Manager**:
The permission model is `receipt_kmitl`'s. *Viewer* reads. *User* (เจ้าหน้าที่การเงิน
หน่วยงาน) issues invoices, files submissions and receives payments; it carries the
receipt app's User tier, since the officer who issues an invoice also receipts it. The
*Submission Approver* is an independent checkbox — the treasury office: it accepts or
rejects a submission, sends it to accounting and is the only role that may cancel an
issued invoice. It carries real accounting rights, so the entries are raised by the acting
user, never as superuser — which also means it must be able to see the accounting entries
of the units it serves: `account_operating_unit` puts its own read rule on `account.move`,
and `invoice_kmitl_operating_unit_access_all` bypasses only the invoice and submission rules,
not that one. *Manager* holds both and may also take back a submission already
sent to accounting — but only while every ใบตั้งหนี้ it raised is still an untouched draft
and every invoice in it is still `issued`; after that, invoices are cancelled one by one. Who sees which record is the Operating Unit's job
(`invoice_kmitl_operating_unit`), not these groups'.

## Reports see the lag

Between `issued` and the moment accounting posts the ใบตั้งหนี้, an invoice is in the
debtor register but in **neither** finance report (`finance_kmitl_reports`
รายงานการตั้งลูกหนี้ and รายงานลูกหนี้ถึงกำหนดชำระ) and not in the accounting dashboard's
`unpaid_ar` card: all three read `state = 'posted'`, and so does Aged Receivable unless the
reader asks for drafts. The draft shows on the dashboard only as a *draft document* of
whoever created it — the treasury officer who sent it, not the accounting makers who must
submit it; they find it under บัญชี ▸ ลูกหนี้ ▸ ใบตั้งหนี้. That lag is accepted. The register
is what the department and the treasury office read; the reports are what the books say.

## Known limitations (accepted, revisit later)

- **The receivable leg carries the dimensions.** `accounting_kmitl` copies the header's
  `analytic_distribution` onto every line, the receivable one included, and the
  invoice needs that header distribution for the receivable reports. A receipt's leg
  carries the same distribution as its invoice's, so the standard analytic balance of the
  pair is zero (`receipt_kmitl` ADR-0004). The reports that read revenue
  (`budget_revenue_comparison`, which filters by account type and code) and Aged
  Receivable (which resolves the dimensions to moves) are unaffected — **but** the Trial
  Balance and General Ledger apply a dimension filter straight to move lines, so a trial
  balance filtered by department now includes the movements of the receivable control
  account. The payable side already behaved this way; the receivable side is new.
- **Revenue moves from a cash to an accrual basis for invoiced items.** A receipt raised
  without an invoice recognises revenue when its remittance is posted. An item that was
  invoiced is recognised when the ใบตั้งหนี้ is posted: an invoice issued in September
  and collected in October lands in the first fiscal year, its cash in the second.
  `budget_revenue_comparison` therefore reads a mixed basis, and its users must be told.
- **No part payments and no credit notes for a part.** An invoice is paid in full or
  cancelled in full ("issued by mistake"). Cancelling is the treasury office's, and an
  invoice that has been paid cannot be cancelled until its receipt is.
