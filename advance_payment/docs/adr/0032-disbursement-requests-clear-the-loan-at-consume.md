# Disbursement requests clear the loan at ตัดงบ

Status: accepted (amends ADR-0028's "closing is a manual, loan-officer-only act"; not in
production, so `advance_payment_disbursement` is rebuilt without migration)

A Disbursement Request of payment type เงินยืม is a **ใบเบิกชดใช้เงินยืม**: it books
spending the borrower already paid out of a loan. It names the loan
(`advance_payment_id`, เลขที่สัญญายืมเงิน), required at submit; a loan may be cleared by
many requests. The picker offers every ค้างชำระ loan of the request's operating unit,
searched as sudo — a requester needs no right on loans.

- **Fed at ตัดงบ.** ส่งใช้คืน (`actual_expense_amount`) is the sum of
  `budget_consumed_amount` over the loan's requests, re-synced after the consume act and
  after a cancel. Not at submit (still revisable) nor at payment (no money moves). The
  consume act is refused unless the loan is ค้างชำระ and the request's amount is within
  คงเหลือ.
- **Borrower-only payees.** Every line pays the loan's borrower; the request pays no
  money out (`disbursement.request.pays_out` is false), so it carries no payment method
  and needs no bank account.
- **Auto-close / auto-reopen.** คงเหลือ reaching 0 closes the agreement (`done`); a
  cancelled request that leaves something owed again reopens it. Both run as the system,
  bypassing the loan officer/admin gates of `action_close`/`action_reopen`.
- **Bridge rebuilt.** `advance_payment_disbursement` drops the loan auto-fill on
  requests raised from a PO or a PR approval (those pay the vendor, payment type
  จ่ายตรง) and the gating that hid "สร้างใบขออนุมัติจัดซื้อ" on an advance PR until its
  loan was ค้างชำระ.

## Consequences

- Budget commitment and dimensions on a ใบเบิกชดใช้เงินยืม are untouched: it is consumed
  like any request. A request with "Consumes Budget" off clears nothing.
- Returned cash (ใบเสร็จ) is still not linked: a loan with leftover cash needs the loan
  officer's manual close.
