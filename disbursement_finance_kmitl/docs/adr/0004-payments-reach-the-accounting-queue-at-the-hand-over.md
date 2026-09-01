# 0004 — A payment reaches the accounting queue only at the Hand-over (จ่ายครบ)

- Status: **superseded by ADR-0005**
- Date: 2026-08-12
- Refines: ADR-0001 (its last consequence no longer holds)

> **Superseded.** This decision handed the voucher over *already submitted*, so the
> accounting office's own maker step was skipped and nobody there could correct the
> booking (the analytic dimensions above all). ADR-0005 keeps the Hand-over and the
> single confirmation but moves the finance office off `state` entirely, so the voucher
> arrives in `draft` and the accounting maker-checker runs from the beginning. What
> follows is kept for the reasoning and the alternatives it rejected, which still hold.

## Context

ADR-0001 settled that a DR payment is posted by the accounting office through the
`account.move` maker-checker, and accepted as a consequence that the payment
**sits in that approval queue from the moment finance submits it** — Submit is
what `finance_kmitl` needs to make a payment exportable to the bank — relying on
the posting guard to stop it being posted too early.

That queue turned out to lie to the people reading it:

- The Approval List filters on `workflow_state = "to_approve"` and nothing else
  (`accounting_kmitl_workflow/static/src/approval_queue/approval_queue.js`), so
  the accounting office is shown payment vouchers that `_post` will refuse.
- `accounting_kmitl_workflow` gives `submitted` a settled meaning for a journal
  entry: the maker has acted and the approver may post. A payment submitted so
  that finance can build an e-payment file reads to the accounting office as
  exactly that.
- The bank's result file is **never imported into Odoo**. A rejected transfer is
  chased and settled outside the system, so the moment a payment becomes
  postable is a moment only the finance office can name.

The two fields to say this with already exist and were already meant to be kept
apart — `state` is the accounting lifecycle, `workflow_state` is the approval
cycle — but `account.payment.action_submit` wrote both in one breath.

## Decision

**Submit on a payment locks and numbers it, and nothing more.** It sets
`state = submitted` (which is all the e-payment export gate wants) and no longer
sets `workflow_state = "to_approve"`.

**A payment requests approval at its Hand-over**, the one moment it stops being
the finance office's work and becomes the accounting office's:

- a payment on a disbursement request hands over when the **request** reaches
  `paid` — per request, whole or not at all;
- a payment made outside a request hands over when finance asserts its result.

**`action_confirm_paid` is the single human confirmation of the payment phase.**
It *writes* `bank_result_status = "success"` on every active payment instead of
demanding that someone set it elsewhere first, and its precondition becomes a
fact Odoo actually holds: every payment that travels in a file has
`export_status = "exported"`. It also submits any payment still in draft — a
cheque or cash payment never had to be locked for a file, and Submit asserts
nothing this confirmation does not already imply — so that every voucher reaches
the accounting office locked and numbered.

The per-row and per-batch result buttons on the e-payment file remain as the
finance office's own bookkeeping and gate nothing.

## Alternatives rejected

- **A new `account.move.state` value (`exported`) for the export gate to filter
  on.** `state` is shared by every journal in the system: the value would have to
  be added to the selection, given an `ondelete`, threaded through status bars and
  translations, and every voucher type that never enters a bank file would have to
  answer what it means for them. The distinction being drawn is not about the
  accounting lifecycle at all.
- **Making the finance side genuinely model-independent** — building the
  e-payment file from `disbursement.payment.line` and creating the
  `account.payment` only once the money has left. This is what real independence
  would take, because `account.payment` is `_inherits`-bound to `account.move`
  and cannot exist without one. Rejected on cost: `bank.payment.export` and the
  four bank-format modules are built entirely on `account.payment`
  (`export_line_ids.payment_id`), and cheque, cash and non-DR payments would need
  a second export mechanism alongside the first.
- **Handing over per payment as each result arrives.** The DR guard in `_post`
  would still refuse the payments whose request is not `paid`, so the queue would
  lie again — and about exactly the payees whose transfers succeeded first.
- **Keeping the per-payment result as a precondition of `action_confirm_paid`.**
  It checks that a person pressed another button, not that anything happened:
  Odoo never learns the bank's answer, so the check is ceremony, and it costs the
  finance office a second pass over the same payees.

## Consequences

- The Approval List holds only entries the approver can actually post. The guard
  in `account_move._post` becomes a safety net instead of the mechanism.
- On a payment, `submitted` means "locked and numbered" and only
  `workflow_state` says whose turn it is. The two offices read different fields on
  one document — the independence that was asked for, without splitting the
  record.
- A ใบสำคัญจ่าย number is assigned at Submit and can sit unposted while the money
  is at the bank. The accounting office accepted this; the alternative was to
  delay numbering until the money left, which only the rejected model split
  allows.
- A payee whose transfer bounces is settled outside Odoo, and the request hands
  over whole — so the payees whose transfers succeeded wait for the ones whose
  did not.
- `submitted_by` on a payment voucher is a finance officer, and the Approval
  List's "Submitted By" column reads that way. This is right: the finance office
  is the maker of ใบสำคัญจ่าย, the accounting office only approves it.
- Approvers get a Todo for payment vouchers for the first time (payments never
  scheduled one), and they get it at the Hand-over rather than at Submit.
- **Open, not decided here:** `action_reject` and `action_draft` still send a
  submitted or awaiting-approval move back to `draft`. After the Hand-over the
  money has already left, so resetting a payment voucher to draft is a state the
  workflow ought to refuse outright — a reversal being the only way back. It
  needs its own decision.
