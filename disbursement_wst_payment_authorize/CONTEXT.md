# Disbursement Work Station: payment_authorize

One station of the disbursement route (see `disbursement_wst/CONTEXT.md` for the
vocabulary). Code `payment_authorize`: the rector's delegate authorises the money to be paid.
Must follow `payment_audit`. Completing it **raises the vouchers** — one `account.payment` per
payment line, numbered and confirmed for the bank (`_create_payments`, in the bridge). Raising
them is not part of the authorisation's transaction: a coordinate that fails leaves the request
authorized with the reason in the chatter. See `disbursement_finance_kmitl` ADR-0006.
