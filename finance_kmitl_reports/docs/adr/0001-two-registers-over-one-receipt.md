# Two registers over one receipt

รายงานการรับเงิน (`finance_kmitl_reports.receipt.report`) and the existing **Receipt
Summary Report** (`receipt_kmitl_summary_report`) both read `kmitl.receipt`, and a reader
meeting the second one for the first time could reasonably ask why a new report was
written at all instead of adding a filter to the old one. It was not, and both stay.

The two answer to different desks, which is what the Finance app and the Receipts app
are for (`finance_kmitl` ADR-0005 — an app says *whose desk is this*). The Receipt
Summary Report is the issuing department's own register: every receipt it wrote, open on
a remittance or a date range, so a department can account for its own counter. รายงานการ
รับเงิน is the treasury's: only receipts whose money has actually reached it
(`state = 'done'`), open on a date range alone, because the treasury does not work by
remittance — it works by the day the money arrived. Filtering the department's report
down to `done` would not produce the treasury's report; it would produce the department's
report with most of its rows hidden, still shaped for a desk that is not asking this
question, and still missing the six-dimension filter bar, the two-level grouping, and the
PDF/Excel layout every other KMITL finance report shares.

## Consequences

- **Two reports over the same table.** Accepted: a receipt written today sits on the
  department's report today and joins the treasury's only once its remittance posts.
  That gap is not the reports disagreeing by mistake — it is the two offices correctly
  disagreeing for as long as the money is in transit.
- **`receipt_kmitl_summary_report` is untouched.** Nothing about its domain, its columns
  or its own PDF/Excel changes; รายงานการรับเงิน is an addition, not a replacement.
- **A reader has to be told which is which.** Documented in `CONTEXT.md` ("รายงานการรับเงิน
  is not the Receipt Summary Report") rather than left to be discovered by diffing the
  two domains.

## Rejected alternatives

- **Add a "remitted only" filter to the Receipt Summary Report.** Keeps one report but
  leaves it shaped for the department's question (open on a remittance, every receipt but
  a cancelled one, no dimension filter bar, no two-level grouping) — a treasury officer
  would still be working a screen built for someone else's desk.
- **Replace the Receipt Summary Report with the new one.** Would take the department's own
  register away from the department that reads it every day, for the sake of a screen
  that was never built to answer their question either.
