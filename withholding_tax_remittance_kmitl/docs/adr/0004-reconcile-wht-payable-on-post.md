# Reconcile the WHT payable account on remittance post

Status: supersedes [ADR-0001](./0001-wht-remittance-plain-je-no-reconcile.md)

## Context

ADR-0001 kept `2120000010` / `2120000099` unreconciled and made
`withholding.tax.cert.remittance_id` the sole "นำส่งแล้ว" record. That works for
the certificate list, but opening the General Ledger or Trial Balance for
either account still shows one growing, opaque balance — there is no way to
tell, from the GL itself, which lines are still owed and which have already
been remitted. An accountant has to leave the ledger and open the certificate
list to answer that question.

ADR-0001 rejected reconciliation mainly because it looked like a one-way door:
turning `reconcile` on for an account with years of unreconciled history
normally means writing a migration to backfill `amount_residual` for every
existing line. That fear turns out to be unfounded — Odoo already does this
for free. `account.account.write({"reconcile": True})` calls
`_toggle_reconcile_to_true()`
(`odoo/addons/account/models/account_account.py:630`), which runs a single
`UPDATE account_move_line SET amount_residual = ...` over every existing line
on the account. No custom migration is needed to flip the flag safely.

## Decision

`withholding.tax.remittance.action_post` now reconciles the WHT payable debit
line(s) on the remittance's journal entry against the WHT payable credit
line(s) on each certificate's source entry, via a new `_reconcile_move()`
called right after the move is posted.

- **Still gated on the account, not the module.** `_reconcile_move()` no-ops
  if `wht_account_id.reconcile` is `False`. Nothing in this module ever writes
  `reconcile` on an account — an accountant turns it on by hand in the chart
  of accounts, in Settings, when they're ready. Until then, posting behaves
  exactly as it did under ADR-0001: a plain, unreconciled JE.
- **`remittance_id` remains the source of truth for "นำส่งแล้ว".** Reconciliation
  is a GL-readability side effect, not a new state. `remit_state` still reads
  off `remittance_id`; nothing about the certificate model changes.
- **One reconciliation per remittance, not per certificate.** All of a
  remittance's WHT payable debit lines are reconciled against all of its
  certificates' source credit lines in a single `reconcile()` call, because
  `_prepare_move_line_vals` doesn't tie a specific remittance line back to a
  specific certificate, and the two sides balance for the whole move anyway
  (`cert.amount_total` always equals the sum of that certificate's own source
  WHT lines — `l10n_th_account_tax._preapare_wht_certs` groups by partner per
  JE, so there's never a leftover fraction to match).
- **A backfill button for certificates already remitted before the flag was
  turned on.** `action_reconcile()` lets an accountant re-run
  `_reconcile_move()` against `posted` remittances after switching Allow
  Reconciliation on. It is idempotent: lines already reconciled are excluded
  by the `not l.reconciled` filter, so pressing it again, or including an
  already-matched remittance in a multi-select from the list view, changes
  nothing for that remittance.

## Accepted side effect

Resetting the *source* voucher/payment back to draft
(`account.move.button_draft`) calls `line_ids.remove_move_reconcile()`
unconditionally, which silently un-reconciles the WHT payable line — while the
remittance itself stays `posted` and its certificate stays "นำส่งแล้ว". This is
not guarded against: guarding it would mean overriding core's `button_draft`
just for one account, for a case (redoing an already-remitted payment) that is
rare and already surprising for other reasons. The GL reconciliation is a
convenience for reading the ledger, not a lock; `remittance_id` remains
correct regardless of whether the two lines happen to still be matched.

## Why not just reconcile everything retroactively via a migration

Because there is no need to: `action_reconcile()` covers the backfill case,
and it only runs when an accountant explicitly asks for it, on the accounts
they've explicitly opted in. A migration would reconcile silently and
unconditionally the moment the module updates, with no chance to review the
account first.
