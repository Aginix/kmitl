# Disbursement Work Station: Billing

The billing (ตั้งหนี้) station of the disbursement route (see `disbursement_wst/CONTEXT.md`).
Code `bill`, group `accounting_kmitl.group_accounting_kmitl_user`, must follow `approve_rector`.

The accountant creates the vendor bill(s) from the request; the bills are posted through the
`account.move` approval (Approve = post). The station completes by itself when the last active
bill is posted (`_on_bills_posted`), so it has no Proceed press of its own and is the one
station completed by a business event rather than by `act()`.

`disbursement_accounting_kmitl` keeps only the capability (`bill_ids`, `_create_bill()`,
`_prepare_bill_line_vals()`, related journal entries); the ordering lives here.
