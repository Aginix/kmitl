# Expense report and in-app returns removed until the ใบเบิก / ใบเสร็จ links exist

Status: accepted (supersedes the report/return parts of ADR-0003 and ADR-0021;
not in production, so no data is carried over beyond moving `reported` /
`to_reconcile` agreements back to `in_progress`)

After the transfer an agreement is now simply **ค้างชำระ** (`in_progress`) until
the loan officer closes it (`action_close`, → `done`). The borrower's expense
report (`reported`, ส่งเบิก/ตรวจรับรายงาน), the in-app return of leftover cash
(`to_reconcile`, `advance.payment.return.line` and its wizard, return installments,
over-return donation) and the borrower's "ส่งรายงานค่าใช้จ่าย" To-Do are gone.

Clearing will come back through the documents that already carry the money:
spending through Disbursement Requests (ใบเบิก) linked to the loan, and returned
cash through receipts (ใบเสร็จรับเงิน). Building those links is separate work, so
the loan is kept minimal now rather than shipping a report and a return flow that
would be replaced. `actual_expense_amount` (ส่งใช้คืน) and `amount_remaining`
(คงเหลือ) stay, read-only, as the fields those links will feed.

## Consequences

- Until the links exist, the debt is cleared outside the app and ส่งใช้คืน stays 0;
  closing is a manual, loan-officer-only act.
- `agx_approval_advance_payment` lost its "ดึงยอดจากใบขออนุมัติ" prefill and the
  expense-divergence warning, which compared against the removed report.
- The follow-up digest shows คงเหลือ instead of the removed ยอดที่ต้องคืน.
