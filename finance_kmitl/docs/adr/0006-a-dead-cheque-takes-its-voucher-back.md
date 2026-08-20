# A dead cheque takes its voucher back

A cheque that dies after it was handed over is cancelled, and cancelling it writes its
voucher's `finance_state` back from `paid` to `confirmed`. A replacement cheque is then
written **on the same voucher**. This is the first and only way backwards in the payment
phase, and it is refused once the accounting office has posted the entry.

`finance_kmitl` ADR-0004 left this open in as many words: *"After the Hand-over the money
has already left, so resetting a payment voucher to draft is a state the workflow ought to
refuse outright — a reversal being the only way back. It needs its own decision."* Cheques
are what force the decision, because a cheque is the one instrument that can fail **after**
the payee has it in their hand. A transfer the bank rejects is settled outside the system
and the payee ends up paid; a cheque that bounces, is lost, is written wrong, or is never
presented until it goes out of date leaves the payee unpaid and a fresh piece of paper to
write. Four causes, one shape: the paper is dead and the obligation is not.

**มอบเช็ค asserted that the money reached the payee.** When the cheque dies that assertion
was false, and the honest thing is to withdraw it rather than to leave it standing and
correct its consequences downstream. So the voucher goes back to `confirmed` — the finance
office's again, still numbered, its money side still frozen, and no longer postable.

**The obligation does not move, so the voucher does not either.** The bill, the payee, the
amount, the analytic dimensions and the ใบสำคัญจ่าย number are all exactly what they were;
only the instrument changed. Issuing a second voucher would put a second number on a
single obligation and read, to anyone counting vouchers, as a second thing owed.

## Consequences

- **The request does not follow the voucher back.** A disbursement request that has crossed
  to `paid` stays there. Its `payment_status_display` drops to จ่ายแล้ว *n-1*/*m*, which is
  legible and true, and the accounting office keeps the Todo it was given, which is also
  true: the request's other payees still need booking. Un-crossing would take work back off
  people who have already started it, over one payee out of twelve.
- **Nothing new guards posting.** `account_move._post` already refuses a voucher whose
  `finance_state` is not `paid`, so withdrawing the assertion blocks the entry as a
  side-effect of saying the true thing. The rule did not have to be restated anywhere.
- **A posted entry is refused, and the message says whose job the fix is.** Once the
  accounting office has posted, the bank credit is in the books; taking it out is a
  reversal on their form under their maker-checker. The finance office does not reach
  across and undo it. In practice this is rarely hit — a voucher sits in their queue for as
  long as their two steps take, which is where a dead cheque is almost always caught.
- **The cancelled cheque keeps its number.** A spent number is never handed to a second
  payee, so the row stays, holding the number and the reason, and the uniqueness constraint
  counts it. This is also what keeps the next guess past it.
- **The reason is a field, not five states.** Bounced, lost, out of date, drawn wrong,
  spoiled in printing: to the register these are one fact — the number was spent and nobody
  was paid — so there is one `cancelled` state and a `cancel_reason` beside it. The old
  model's `bounced` state named one cause out of four and had nowhere to put the others.
- **Cancelling without replacing is allowed.** The wizard defaults to writing a
  replacement, because that is what is nearly always meant, but a disbursement that is
  being unwound entirely needs the cheque dead and no successor.
- **A cross-month replacement moves the withholding.** The certificate is dated from the
  cheque (ADR-0005), so a cheque dated 30 September replaced by one dated 3 October moves
  that payee's withholding from the September ภ.ง.ด. to October's. If September was already
  filed, the finance office files an amendment. The system's job here is only to stop
  saying a date that is no longer true.

## Rejected alternatives

- **Cancelling the voucher and raising a new one.** Clean in the books and wrong about the
  world: nothing new is owed, so nothing new should be numbered. It also cannot be done
  where it is needed — `_create_payments` refuses any request that is not
  `payment_authorized`, and a request with a dead cheque is at `paid` or `cleared`, so the
  replacement voucher would be born outside its request and break the rule that everything
  in this phase leads back to the ใบขอเบิก.
- **Leaving the voucher `paid` and recording the death as a note.** This is how a rejected
  transfer is handled — settled outside the system, vouched for by the one confirmation —
  and it does not carry over, because a replacement transfer is made at the bank's portal
  and needs nothing from Odoo, while a replacement cheque has a **number** that has to
  reach the register or the register is not a register.
- **Sending the request back to `payment_authorized` with the voucher.** Symmetrical, and
  it withdraws work from the accounting office for reasons that have nothing to do with the
  eleven payees they can already book. The request's counter says what is outstanding
  without moving anybody's queue.
- **Letting the finance office reverse the posted entry from here.** It would make the
  cancel button work in every case, by having one office post entries on another's behalf.
  The whole two-lifecycle split (ADR-0005 in `disbursement_finance_kmitl`) exists so that
  does not happen.
- **Allowing the withdrawal only before the Hand-over.** Simple, forward-only preserved,
  and it leaves the commonest real case — a cheque handed over on Monday and returned on
  Friday — with nothing to do but a manual journal entry.
