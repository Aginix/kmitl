# Disbursement Work Station: clear

One station of the disbursement route (see `disbursement_wst/CONTEXT.md` for the
vocabulary). Code `clear` (ล้างหนี้): the accounting office books the payment vouchers. Must
follow `pay`. The maker submits the vouchers (`action_submit_payments`, singly or from the queue);
the approver posts them through the same account.move maker-checker as the vendor bill, and
posting the last one completes the station (`account_move._post`) — the posting is the
authority, so no group check. A voucher cannot post before the request reaches this station.
