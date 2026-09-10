# WHT payable is cleared by a plain JE + a persistent remittance document, not by GL reconciliation

## Context

`l10n_th_account_tax` books every withheld amount as a credit to a WHT payable
account (`2120000010` / `2120000099`) and never clears it. Once KMITL remits
the tax to the Revenue Department, that credit has to come down, and the
office needs to know which certificates have already been remitted and which
haven't.

The obvious accounting-textbook answer is: give the account `reconcile=True`
and reconcile the withholding credit lines against the remittance's debit
line, the same way a payable account is reconciled against its payment.

## Decision

We do **not** do that. `withholding.tax.remittance.action_post` books a plain,
unreconciled `account.move` (`Dr` WHT payable / `Cr` bank), and the durable
"already remitted" fact lives on `withholding.tax.cert.remittance_id` — a
Many2one to the remittance that cleared it — not on any GL reconciliation
state. The payable accounts keep `reconcile=False`.

## Why

- **Hard to reverse.** Turning `reconcile` on for `2120000010`/`2120000099`
  after the fact requires migrating every historical line's reconciliation
  state (or leaving old lines forever unreconciled next to new ones that are).
  Deciding against it now, while the accounts have never been reconciled, is
  cheap; deciding *for* it later, once the pattern below is live, is a real
  data migration.
- **Surprising.** A reader who knows Odoo accounting expects "clear a
  payable" to mean reconciliation. It doesn't happen that way here on
  purpose: the WHT payable is not a per-partner payable like
  `liability_payable` — a remittance clears a slice of the *whole* account
  balance for one ภ.ง.ด. form, not a specific certificate's line against a
  specific payment's line. Reconciliation is built for the latter shape, not
  the former.
- **Real trade-off, taken deliberately.** Skipping reconciliation means no
  chart-of-accounts change and no balance migration, at the cost of no
  line-level GL matching between a withholding credit and the remittance debit
  that cleared it. That trade is acceptable because the cert→remittance link
  already answers the question a reconciliation would: which certificates are
  ยังไม่นำส่ง and which are นำส่งแล้ว, still visible and filterable without ever
  opening the ledger.
