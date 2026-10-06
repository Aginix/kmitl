# Disbursement Work Station: payment_audit

One station of the disbursement route (see `disbursement_wst/CONTEXT.md` for the
vocabulary). Code `payment_audit`: the auditor checks the disbursement documents after the
bills are posted and sets the เรื่องที่จ่าย that gives every payee its paying account. Must
follow `bill`. Entering it makes the payment lines (`_ensure_payment_lines`); completing it is
refused until every payee has usable banking coordinates. It is the **only** checkpoint on those
coordinates — see `disbursement_finance_kmitl/CONTEXT.md`.
