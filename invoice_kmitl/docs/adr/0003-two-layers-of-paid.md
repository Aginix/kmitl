# Two layers of "paid": the department's and the books'

An invoice has two truths about being paid, kept apart on purpose.

- **Operational — `kmitl.invoice.state = 'paid'`.** The department took the money and
  issued the receipt. It is set the moment the receipt is created, as a draft.
- **The books — `move_id.payment_state`.** The accounting office has posted both the
  ใบตั้งหนี้ and the receipt's entry and the receivable has been reconciled. Shown on the
  invoice as the **Accounting Payment Status** and **Amount Due (Accounting)**, related
  fields that read as superuser so a department user needs no right on `account.move`.

## Two gaps, treated differently

- **A lag that is accepted.** Between "the department has the money" and "the receivable is
  reconciled" the receipt is drafted, remitted, approved, posted, and its entry submitted
  and approved by the accounting office. Days may pass. The two statuses side by side in
  the debtor register are how that stretch — money on its way — is seen, and it is normal.
  The same is true before the ใบตั้งหนี้ is posted: the invoice is in the register but in no
  finance report (`CONTEXT.md` → Reports see the lag).
- **A drift that is not accepted, and is prevented.** A manager who resets a **posted**
  remittance to draft reverses each receipt's entry with `_reverse_moves(cancel=True)`,
  which first **removes every reconciliation** touching the entry and then auto-posts the
  reversal past the maker–checker. The ใบตั้งหนี้ returns to `not_paid` in full while the
  invoice would stay `paid` for ever. `kmitl.receipt.remittance.action_draft` is therefore
  extended: after the normal reset, each receipt that settled an invoice is **cancelled**
  through the ordinary cancel path (which detaches it from the remittance), and
  cancelling a receipt issues its invoice again, with a note in both chatters.
  The receipt is cancelled rather than left a draft because a draft that kept its invoice
  could be remitted again while the debtor is receipted a second time.

## Reconciliation

- **Trigger.** `account.move._post` is overridden — after `super()`, and on **the value it
  returns**. `_post(soft=True)` leaves a move dated in the future unposted and returns only
  the moves it posted, and `reconcile()` refuses a move that is not posted. Whichever of the
  two entries is posted last triggers it; the first finds its counterpart unposted and
  stays silent. Entries are linked to their invoice by `account.move.kmitl_invoice_id`,
  stamped on the ใบตั้งหนี้, on the receipt's entry and on a credit note, so the hook
  costs nothing on any other move.
- **The manual button.** **Reconcile** on the invoice (treasury office) does the same
  work and raises with the reason when there is nothing to reconcile.
- **A refusal never blocks the posting.** The automatic path runs in a savepoint and turns
  a `UserError` — what `reconcile()` and the operating-unit guard raise — into a chatter
  note on the invoice, because whoever posts is not the one who can mend an invoice.
  Anything else is a bug and is left to surface.
- **Superuser, deliberately, for the lookup and the reconciliation.**
  `account_operating_unit` puts a global read rule on `account.move` and
  `account.move.line`, and this repository has no `account_operating_unit_access_all`. A user
  outside the counterpart's operating unit would search for its lines, find none, and the
  reconciliation would be skipped without a word. The guard lives in
  `invoice_kmitl_operating_unit`: lines in more than one operating unit are refused,
  because `account_operating_unit` overrides `reconcile()` to book an inter-OU balancing
  entry and **auto-post** it past the approval when a cash or bank journal is involved.
  It is dormant today only because nobody sets `ou_is_self_balanced`.

## Cancelling

An issued invoice is cancelled in full ("issued by mistake"), by the treasury office
only. A paid one cannot be: its receipt is cancelled first. What happens to the
ใบตั้งหนี้ follows what the accounting office has done with it: a draft is deleted, one
awaiting approval is theirs to send back, and a posted one is reversed by a draft
`out_refund` that goes through the same submit and approve and is reconciled against the
original on posting — the invoice's `payment_state` ends `reversed`, not `paid`, which is
what core means by it.
