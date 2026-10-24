# The invoice is its own document, and what it raises is an `out_invoice`

A department that wants to bill a debtor needs a document it can number, print and
hand over the same day, and the accounting office needs a receivable it can book,
approve and reconcile. These are two documents with two owners, so the invoice
(`kmitl.invoice`) is a model of its own and, once the treasury office sends it on, it
raises a draft `out_invoice` — the ใบตั้งหนี้ `finance_kmitl_reports` already reads. The
two are 1:1 and tied by `out_invoice.ref = invoice.name` and `account.move.kmitl_invoice_id`.

## Considered options

- **The department keys the `out_invoice` itself.** Rejected. Departments never touch
  `account.move` (`receipt_kmitl` ADR-0003): giving them the right would hand every
  department officer the accounting office's journal, and the officer would also have to
  pass the accounting form's own rules (four dimensions, the maker–checker
  workflow). It would also put the debtor's number — which must exist before accounting
  books anything — in the accounting office's hands.
- **`kmitl.invoice` raises a journal entry (JV) with hand-built receivable lines.**
  Rejected. รายงานการตั้งลูกหนี้, รายงานลูกหนี้ถึงกำหนดชำระ and the accounting
  dashboard's `unpaid_ar` card read an `out_invoice` and its `payment_state`; a journal
  entry is none of the three. Core computes `payment_state` only for invoice-type moves,
  from the lines whose `display_type` is `payment_term` — a hand-built JV has neither — so
  the debt could never show as paid and would be missing from both finance reports.
  (Aged Receivable reads open receivable lines and would have shown it.) Raising the
  `out_invoice` the accounting office would have keyed anyway gets all of those for free,
  with no change to a report.
- **One number for both.** Rejected. Writing `IV/…` into `account.move.name` would
  corrupt the AR journal's `_get_last_sequence`. The debtor holds the `IV/…` number; the
  accounting office issues its own `AR/…` when it submits.
- **Chosen: two documents, one raised from the other.** The invoice is created, numbered
  and printed by the department; the ใบตั้งหนี้ is created, as a draft, when the treasury
  office sends the submission to accounting, and goes through the accounting office's
  ordinary submit and approve.

## Consequences

- **The `out_invoice` is built the way core builds one, not as lines.** Core makes the
  receivable line itself from `partner.property_account_receivable_id`, and counts
  `amount_residual` only on lines whose `display_type` is `payment_term`. The entry is
  therefore created from `invoice_line_ids` alone, the way
  `disbursement_accounting_kmitl` creates its bills.
- **No VAT, said out loud.** Every line is created with `tax_ids` cleared. Today the chart
  holds no sale tax, but the day an administrator puts one on a product, an invoice would
  silently carry VAT.
- **`invoice_date` is the invoice's, and the payment term is empty.** Left blank, core
  stamps the day of posting on the entry; a multi-instalment term would split the
  receivable into several lines and overwrite the due date.
- **A partner without a receivable account stops the batch.** `action_done` refuses, naming
  the partner, rather than letting Odoo fail deep inside entry creation.
- **The accounting office is not the creator, so Submit had to be opened to it.**
  `accounting_kmitl_workflow` lets only the creator (or an administrator) submit an entry.
  An entry raised for a KMITL invoice has no accounting author, so
  `account.move._check_submit_allowed` and `_compute_can_submit` exempt it — the same
  exemption `finance_kmitl` makes for a payment voucher handed over by another office. The
  override declares only its own dependency: the dependencies of a compute accumulate over
  its overrides.
- **The treasury office may delete a draft ใบตั้งหนี้ only with `force_delete`, in the
  case that matters.** Core refuses to delete a numbered entry that is not the last of
  its chain unless the user holds `account.group_account_manager` (or `force_delete` is in
  the context); the treasury office holds only `group_account_invoice`. KMITL numbers an
  entry when the accounting office submits it, so a draft that was never submitted deletes
  freely, but one that was submitted and then reset to draft carries a number.
  Cancelling an issued invoice whose entry is still a draft therefore deletes it with
  `force_delete`.
