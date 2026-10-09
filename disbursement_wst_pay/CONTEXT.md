# Disbursement Work Station: pay

One station of the disbursement route (see `disbursement_wst/CONTEXT.md` for the
vocabulary). Code `pay`: the finance office puts the raised vouchers in e-payment files and
the money leaves. Must follow `payment_authorize`. **Nobody presses this station for the request
as a whole**: closing an e-payment file pays the vouchers it carried, handing a cheque over pays
its payee, cash is confirmed on the voucher, and the request crosses (the **Hand-over**) when the
last of them lands — `_try_hand_over_when_all_paid`, which completes the step without a
group check because the payments being paid is the authority. `action_confirm_paid` is the
developer-mode way past a stuck voucher. See `disbursement_finance_kmitl` ADR-0004 and ADR-0007.
