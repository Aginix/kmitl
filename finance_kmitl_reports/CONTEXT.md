# CONTEXT — KMITL Finance Reports

The two reports the กองคลัง reads about money going **out**: what was paid, and what
still has to be. Both are read-only views over records the
[`finance_kmitl`](../finance_kmitl/CONTEXT.md) and
[`accounting_kmitl`](../accounting_kmitl/CONTEXT.md) contexts own — this module defines
no document and no state, and every term it uses is theirs.

The receiving side (ใบเสร็จ, ลูกหนี้) is not here. `finance_kmitl` has reserved a
**การเงินรับ** menu for it, and its summary report already exists as
[`receipt_kmitl_summary_report`](../receipt_kmitl_summary_report).

## Terms

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

- **ยอดคงเหลือ / Amount due** (`account.move.amount_residual`): what is left of a bill,
  which is what the report totals. A bill paid in part still costs only what remains of
  it, and a report that totalled face values would ask the treasury for money it has
  already sent.

- **จัดกลุ่ม / Grouping**: both reports fold up to two levels deep, chosen on screen
  rather than fixed by the report. Every level totals, and the totals are the same
  figures on screen, in the PDF and in the workbook because all three read one server
  call. _Avoid_: adding a "report variant" for a grouping — a variant is a dropdown
  value.

## Rules

- **The report is not a second opinion about what a record means.** Which bills are
  still owed is `accounting.kmitl.dashboard._UNPAID_STATES`, borrowed rather than
  restated, so the card the accounting office reads every morning and this report cannot
  disagree. Which vouchers are paid is `finance_state`. Which analytic accounts a
  dimension filter covers is `accounting_kmitl_reports.dimension.filter.mixin` — naming
  a faculty names everything under it, the same reading the routing rules and the
  ใบสำคัญจ่าย list use.
- **Screen, PDF and Excel are one report.** All three call the same `get_report_data`,
  and the columns come from `get_columns` on the server. A figure that differs between
  the screen and the print is the failure the finance office would notice last and trust
  least, so there is nowhere for the three to drift apart.
- **A payment reaches its dimensions through `move_id`.** `account.payment` sees
  `analytic_distribution` through `_inherits`, and an inherited leaf is joined straight
  onto `account.move`'s column without passing through `AnalyticMixin._search` — which
  is the only place the JSON leaf is rewritten into the form the index answers. The
  payment report walks the relation explicitly; the payables report, being on
  `account.move` already, does not have to.

## รายงานเจ้าหนี้ถึงกำหนดชำระ is not Aged Payable

`accounting_kmitl_reports` already has an **Aged Payable**, over the same population,
and the two are easily mistaken for one report written twice. They face opposite
directions:

|         | Aged Payable                            | รายงานเจ้าหนี้ถึงกำหนดชำระ           |
| ------- | --------------------------------------- | ------------------------------------ |
| Looks   | backwards                               | forwards                             |
| Asks    | how long has this been outstanding      | what has to be paid, and by when     |
| Axis    | age buckets counted back from a date    | due date, ascending                  |
| Read by | the accounting office, closing a period | the treasury, planning a payment run |
| Answers | "are we late, and how late"             | "what leaves this week"              |

A bill 90 days overdue is one line in the oldest bucket of Aged Payable and one line at
the top of this report; the same fact, asked for by two offices who do two different
things with it. Neither is derivable from the other by re-sorting, because Aged Payable
aggregates per partner and this report never leaves the bill.
