# Disbursement — Cash Movement

KMITL never pays out of its main savings account directly: money travels through
one or more intermediate bank accounts — the bank auto-sweeps a single cheque
covering many payees down to the account a voucher is actually drawn on.
Accounting does not book that sweep when it happens (one cheque covers payees
with different dimensions); it books the whole chain instead, per payee, at the
moment each voucher's payable is cleared, so every leg carries that voucher's own
dimensions. This context adds the missing legs to a payment voucher that already
correctly books its payable and its paying account.

## Language

**การโยกเงินระหว่างบัญชี (Inter-account Cash Movement)**: the legs added to a
disbursement voucher's **own journal entry** — never a separate one — that trace
the money from its source account down to the paying account (หัวจ่าย) that pays
the payee. Every leg carries the same net amount already credited at the paying
account, and every leg carries that voucher's own dimensions, so the whole chain
reads as one document.
_Avoid_: **การโอนงบ** (`budget.transfer` — moves the budget *pool*, touches no
GL), **โอนเงินและรายได้** (`disbursement_cash_revenue_handover` — a *separate*
entry that re-tags the same GL account on both sides; see
[Cash & Revenue Handover](../disbursement_cash_revenue_handover/CONTEXT.md)),
**Internal Transfer** (Odoo's own `is_internal_transfer`, hidden in
`finance_kmitl`), the word "โอนเงิน" used loosely.

**เส้นทางโยกเงิน (Cash Route)**: `kmitl.cash.route` — one row per (paying
account × sources of funds it serves), naming the accounts money passes through
before it gets there. **A row's existence is the rule**: a paying account with
no row for a voucher's source of funds is a setup gap, surfaced as a
non-blocking warning at Submit — a row that exists but names no intermediate
account means "pays directly", and is silent on purpose.
_Avoid_: หัวจ่าย (`account.payment.method.line` — the destination, not the
route to it), เรื่องที่จ่าย (picks a paying account, says nothing about where
the money came from), central funding chart (a different bridge; see
[Cash & Revenue Handover](../disbursement_cash_revenue_handover/CONTEXT.md)).

**บัญชีระหว่างทาง (Intermediate Account)**: an account money passes through
between the true source and the paying account — `kmitl.cash.route.hop`,
ordered by `sequence`.
_Avoid_: **บัญชีพัก / Suspense** (an unrelated concept; see
[receipt_kmitl](../receipt_kmitl/CONTEXT.md)), Outstanding Payments (KMITL does
not use core's outstanding-account reconciliation flow).

## Known limitations (accepted, revisit later)

- **The intermediate and paying accounts always net to zero once posted; the
  bank statement does not.** The cheque that actually sweeps money into a
  paying account is never itself booked — only this after-the-fact chain, per
  payee — so these accounts never carry the balance a real reconciliation would
  expect. This is the direct, intended consequence of the requirement: KMITL
  wants every voucher tagged with the dimensions of what it paid for, not a
  bank-accurate ledger for accounts nothing is ever billed against directly.
- **Bank reconciliation gains extra lines.** Every account a route touches has
  `reconcile=True` (`account_kmitl/data/account.account.template.csv`), so each
  voucher adds a debit and a credit that net to zero but are not statement
  lines (the same trade-off `disbursement_cash_revenue_handover` accepted).
- **Scope is disbursement vouchers only.** A payment with no
  `disbursement_request_id` grows no legs — advance-payment loans and purchase
  guarantees have no cash route yet.
- **The three paying accounts this module adds are not yet in every เรื่องที่จ่าย's
  `allowed_paying_account_ids`.** จ่ายบุคคล still narrows to the five accounts it
  always has; the routes seeded for the three new accounts serve จ่ายเงินบริษัท
  (whose subjects allow every paying account) until finance adds them by hand in
  Finance ▸ Settings ▸ Payment Subjects.
- **Single currency.** A leg's amount is read straight off the payment's own
  liquidity line; multi-currency vouchers are not accounted for.
