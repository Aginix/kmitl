# CONTEXT — KMITL Finance Reports

The reports the กองคลัง reads about money moving in both directions: what was paid and
what still has to be, what was received and who still owes. Every one of them is a
read-only view over records the [`finance_kmitl`](../finance_kmitl/CONTEXT.md),
[`receipt_kmitl`](../receipt_kmitl/CONTEXT.md) and
[`accounting_kmitl`](../accounting_kmitl/CONTEXT.md) contexts own — this module defines
no document and no state, and every term it uses is theirs.

## Terms — money out

- **รายงานการจ่ายเงิน / Payment Report** (`finance_kmitl_reports.payment.report`): one
  row per **ใบจ่ายเงิน** the treasury has paid, in the period the money left. The
  finance office asked for a daily one and a monthly one; they are this report with two
  date ranges, and nothing else about them differs. _Avoid_: calling it a "voucher list"
  — its axis is the day the money moved, not the day the voucher was raised, and the two
  are different reports of the same records.

- **วันที่จ่ายจริง / Actual payment date**: the axis of that report. Defined in
  [`finance_kmitl`](../finance_kmitl/CONTEXT.md) and read off the instrument that
  carried the money — an e-payment file's effective date, a cheque's own date, or, for
  cash, the voucher date. A voucher authorised on 28 September whose file takes effect
  on 2 October is **October's** payment. See `finance_kmitl` ADR-0009.

- **จ่ายแล้ว / Paid, for the purposes of this report**: `finance_state = 'paid'`, and
  nothing weaker. A file at `done` has been produced and may be sitting undownloaded in
  somebody's browser (`finance_kmitl` ADR-0004), so it is not money out. _Avoid_:
  counting `export_status = 'exported'` as paid.

- **รายงานเจ้าหนี้ถึงกำหนดชำระ / Payables Due Report**
  (`finance_kmitl_reports.payable.due.report`): one row per posted vendor bill that is
  not yet settled, ordered by **วันครบกำหนด**. It is a **schedule**: what has to be
  paid, and by when. This is what an e-payment run is planned against.

## Terms — money in

- **รายงานการรับเงิน / Receipt Report** (`finance_kmitl_reports.receipt.report`): one
  row per **ใบเสร็จรับเงิน** whose money has reached the treasury, in the period it was
  received. Daily and monthly are again one report with two ranges. It is the
  **treasury's** register, not the issuing department's — see the table at the foot of
  this file.

- **ถึงคลังแล้ว / Remitted, for the purposes of this report**: `state = 'done'`, and
  nothing weaker. A receipt at `draft` or `submitted` is money in a department's drawer
  and on its way; only a posted remittance has handed it to the treasury and written the
  entry. The same standard the payment report holds itself to on the way out. _Avoid_:
  reading `submitted` as "remitted" — it means the department has said it will remit.

- **วันที่รับเงิน / Receipt date** (`kmitl.receipt.date`): the day the money was taken
  across the counter, and the axis of that report. Unlike the paying side there is no
  second date to choose between: `kmitl.receipt._prepare_move_vals` dates the journal
  entry with it, so the receipt, this report and the ledger name the same day. A receipt
  written in September and remitted in October is **September's** money, and appears in
  September's report from the moment the October remittance posts.

- **ใบตั้งหนี้ / AR invoice** (`account.move`, `out_invoice`, on the **ใบสำคัญลูกหนี้**
  journal seeded by `account_kmitl`): the document that makes someone owe KMITL money.
  Named for the menu the accounting office opens it from (บัญชี ▸ ลูกหนี้ ▸ ใบตั้งหนี้).
  It is **not** settled by an ใบเสร็จรับเงิน — see the rule below. _Avoid_: "ลูกหนี้"
  unqualified, which in this repo far more often means **ลูกหนี้เงินยืม**
  (`advance.payment`), a different debt with its own follow-up screens in
  [`advance_payment_followup`](../advance_payment_followup).

- **รายงานการตั้งลูกหนี้ / Receivables Raised Report**
  (`finance_kmitl_reports.receivable.raised.report`): one row per **posted** ใบตั้งหนี้,
  on its own **วันที่ใบตั้งหนี้**. A register of debt created, so it keeps a row whether
  or not the debt has since been paid — what became of it is the next report's question.

- **รายงานลูกหนี้ถึงกำหนดชำระ / Receivables Due Report**
  (`finance_kmitl_reports.receivable.due.report`): one row per posted ใบตั้งหนี้ not yet
  settled, ordered by **วันครบกำหนด**. The mirror of the payables report, and read the
  same way: what is owed to KMITL, and by when.

## Terms — shared

- **ยอดคงเหลือ / Amount due** (`account.move.amount_residual`): what is left of a bill
  or an invoice, which is what the due reports total. One paid in part still counts only
  what remains of it, and a report that totalled face values would ask the treasury for
  money it has already sent, or chase a debtor for money already received.

- **จัดกลุ่ม / Grouping**: every report folds up to two levels deep, chosen on screen
  rather than fixed by the report. Every level totals, and the totals are the same
  figures on screen, in the PDF and in the workbook because all three read one server
  call. _Avoid_: adding a "report variant" for a grouping — a variant is a dropdown
  value.

## Rules

- **An ใบเสร็จรับเงิน never settles an ใบตั้งหนี้.** A receipt's entry is a **Dr Cash
  Account / Cr revenue** pair per line (`payment_method_id.account_id` against
  `line.account_id`) and a **Dr Deposit Bank Account / Cr Cash Account** remittance leg
  for the total (`payment_method_id.deposit_account_id`) — see `receipt_kmitl`
  [ADR-0004](../receipt_kmitl/docs/adr/0004-treasury-remittance-leg-in-the-receipt-entry.md).
  Not one of the three legs is a receivable, so receipting a customer who is paying an
  invoice would book the revenue a second time and leave the invoice open. The two
  money-in reports therefore read two different documents and never mix them:
  การรับเงิน counts receipts, การตั้งลูกหนี้ and ลูกหนี้ถึงกำหนดชำระ count invoices.
  Money that settles an ใบตั้งหนี้ is outside every report here until that settlement
  has a workflow of its own.
- **The report is not a second opinion about what a record means.** Which bills and
  invoices are still owed is `accounting.kmitl.dashboard._UNPAID_STATES`, borrowed
  rather than restated, so the card the accounting office reads every morning and these
  reports cannot disagree. Which vouchers are paid is `finance_state`; which receipts
  have arrived is `state`. Which analytic accounts a dimension filter covers is
  `accounting_kmitl_reports.dimension.filter.mixin` — naming a faculty names everything
  under it, the same reading the routing rules and the ใบสำคัญจ่าย list use.
- **Screen, PDF and Excel are one report.** All three call the same `get_report_data`,
  and the columns come from `get_columns` on the server. A figure that differs between
  the screen and the print is the failure the finance office would notice last and trust
  least, so there is nowhere for the three to drift apart.
- **A payment reaches its dimensions through `move_id`.** `account.payment` sees
  `analytic_distribution` through `_inherits`, and an inherited leaf is joined straight
  onto `account.move`'s column without passing through `AnalyticMixin._search` — which
  is the only place the JSON leaf is rewritten into the form the index answers. The
  payment report walks the relation explicitly; the invoice reports, being on
  `account.move` already, do not have to, and `kmitl.receipt` carries all six dimensions
  on its own header.
- **รายงานการรับเงิน sees only what the reader's Operating Unit lets them see.**
  `receipt_kmitl_operating_unit` puts a `global` `ir.rule` on `kmitl.receipt` that scopes
  every `search()` — this report's included — to the reader's own operating units, and
  the only way past it is holding `receipt_kmitl_operating_unit_access_all`'s
  `group_all_ou_receipt_kmitl`, the same group every other cross-OU screen in this repo
  (purchase, budget, advance payment, procurement plan) relies on. Nothing here bridges
  that group to a finance role, and nothing should: who holds it is an IAM/role setting,
  not a code decision, and this report must never `sudo()` past the rule to work around
  it (`accounting_kmitl_dashboard.py`'s own rule against it applies here too). A treasury
  officer missing the group sees an institute-wide report that quietly isn't — check for
  it at UAT, not by reading the domain.

## The due reports are not the Aged reports

`accounting_kmitl_reports` already has an **Aged Payable** and an **Aged Receivable**
over the same populations, and each is easily mistaken for its due report written twice.
They face opposite directions:

|         | Aged Payable / Receivable               | ถึงกำหนดชำระ                         |
| ------- | --------------------------------------- | ------------------------------------ |
| Looks   | backwards                               | forwards                             |
| Asks    | how long has this been outstanding      | what falls due, and by when          |
| Axis    | age buckets counted back from a date    | due date, ascending                  |
| Read by | the accounting office, closing a period | the treasury, planning the week      |
| Answers | "are we late, and how late"             | "what moves this week"               |

A bill 90 days overdue is one line in the oldest bucket of Aged Payable and one line at
the top of the due report; the same fact, asked for by two offices who do two different
things with it. Neither is derivable from the other by re-sorting, because the Aged
reports aggregate per partner and the due reports never leave the document.

## รายงานการรับเงิน is not the Receipt Summary Report

[`receipt_kmitl_summary_report`](../receipt_kmitl_summary_report) reads the same
`kmitl.receipt` rows and is deliberately kept. The two answer to different desks, which
is what the Finance app and the Receipts app are for
(`finance_kmitl` ADR-0005 — an app says _whose desk is this_):

|          | Receipt Summary Report                     | รายงานการรับเงิน                   |
| -------- | ------------------------------------------ | ---------------------------------- |
| App      | Receipts (ใบเสร็จ)                          | การเงิน                            |
| Desk     | the department that issued the receipts    | the treasury that received them    |
| Counts   | every receipt but a cancelled one          | only `done` — money actually in    |
| Asks     | what did this counter take                 | what reached the treasury          |
| Opens on | a remittance, or a date range              | a date range                       |

A receipt written today is on the department's report today and on the treasury's only
once its remittance posts. That gap is not a defect in either report; it is the two
offices disagreeing for as long as the money is in transit, which is exactly how long
they should disagree.
