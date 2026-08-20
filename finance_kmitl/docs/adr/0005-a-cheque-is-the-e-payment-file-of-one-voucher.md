# A cheque is the e-payment file of one voucher

A voucher paid by cheque gets a record of its own — `cheque.register` — sitting between
**ยืนยันพร้อมส่งธนาคาร** and **ยืนยันจ่ายสำเร็จ**, in the place an **ไฟล์ e-Payment**
occupies for a transfer. It is bound one-to-one to the voucher and states nothing the
voucher already states.

The finance office has three ways of paying money out, and until now only one of them had
anywhere to work. A transfer is confirmed for the bank, picked into a file, exported, and
the file is closed; every step is a record and every record is somebody's press. A cheque
went from `confirmed` straight to `paid` with **no place to write the cheque number down
at all** — the one fact that identifies the payment to the bank, to the payee and to the
auditor. There was a `cheque.register`, but it was created at `action_post`, which is
after the money has left and after the Hand-over, by which point the number is a
historical note rather than a thing being decided; and for a voucher on a disbursement
request it was never created at all, because those post through `account.move._post` and
never run `account.payment.action_post`.

So the cheque becomes the record that the finance office's cheque work happens on. What
it is *not* is a second copy of the payment. A file is one instruction covering many
payees, so it genuinely needs its own payees, amounts and dates; a cheque covers exactly
one payee, so the payee, the amount, the currency and the paying account are read through
`payment_id` as related fields and stored nowhere else. What is the cheque's own is the
paper: the number, the book it was torn from, the date written on it, whether it has been
printed, handed over, or died.

## Consequences

- **The cheque book is `payment_method_line_id.bank_account_id`, not a journal.** A
  journal is a voucher type (ใบสำคัญ) and holds no bank account — ADR-0001 — so the old
  register, which took `journal_id` from the payment, was pointing every cheque at PV.
  Its `bank_id` was therefore always empty, one print layout served every bank, and the
  "no repeated numbers per book" constraint collapsed all three of KMITL's cheque books
  into one number space. `account_kmitl`'s own docstring had said the bank account was
  the cheque book since the paying-account model was built; the register simply never
  read it.
- **One voucher has at most one *live* cheque, not at most one cheque.** A cheque that
  died leaves its row behind holding the number it spent, so a voucher accumulates as
  many rows as it took pieces of paper. The constraint is on the ones that are not
  cancelled. See ADR-0006.
- **`draft → issued → paid` and not `draft → paid`**, for the reason ADR-0004 gives for
  the e-payment file: a cheque that is printed and signed can wait days in a drawer for
  the payee to collect it, and "the paper exists" is not "the payee has their money". The
  Hand-over — and with it the request's crossing to the accounting office — happens at
  **มอบเช็ค**, so nobody is asked to book an entry for money that is still in a drawer.
- **The number is guessed, never held.** `next_cheque_number` is computed as one past the
  highest already spent in the same book, and nothing stores a counter. A cheque book is
  pre-printed: the paper decides, and a stored counter that drifted from it would state a
  wrong number confidently. A guess that is wrong is overtyped and nothing downstream is
  any worse off — which is also why a page torn out and thrown away needs no record here.
- **The register does not follow the cheque to the bank.** There is no `cleared` and no
  `bounced`-as-a-state: KMITL keeps no เช็คจ่าย holding account (ADR-0001), so neither
  would move any money, and nobody at KMITL reconciles presented cheques against a
  register. Which cheques are still outstanding is a line in the bank reconciliation, and
  that is the accounting office's paper, not the finance office's list.
- **`is_cheque_payment` becomes a real branch in the workflow**, not just a display flag.
  `action_confirm_paid` refuses a cheque outright: a transfer is confirmed by closing its
  file, a cheque by handing the cheque over, and cash — which nothing else in the system
  records — is what that press is left for.
- **The print layout moves from the journal to `res.bank`.** The bank prints the form, so
  every book held at one bank shares one calibration and no two banks share one. Hanging
  it on the journal had given every bank the same layout; hanging it on the individual
  bank account would ask the treasury office to calibrate one printed form once per
  account.
- **Received cheques leave this model.** `direction` and the inbound register are gone: a
  cheque KMITL takes in is a receipt, `receipt_kmitl` already models it with a payment
  method of its own, and a `payment_id` that is required and points at an outbound
  voucher leaves the inbound half no meaning.

## Rejected alternatives

- **Columns on `account.payment` — `check_number`, `check_date` — with no record at all.**
  This is what Odoo's own `account_check_printing` does, and it is the smaller change. It
  cannot hold a cheque that died and was replaced: the voucher would have one number
  field and the paper it went through would be lost, along with the numbers those pieces
  spent. It also has nowhere to put a lifecycle, so "printed" and "collected" would
  collapse into each other.
- **Using `account_check_printing` itself.** Its cheque numbering hangs off the journal
  (`check_sequence_id`, `check_next_number`), which for KMITL is the voucher type; its
  method is `check_printing`, while `account_kmitl` deliberately retires Odoo's stock
  methods and seeds its own three; and its `_constrains_check_number_unique` scopes
  uniqueness to the journal, which would repeat the very bug being fixed here. What was
  worth taking from it was taken: comparing cheque numbers as integers rather than as
  text, and proposing the next one rather than assigning it.
- **A batch document over several cheques, mirroring the e-payment file exactly.** The
  file is a batch because the *bank* receives one file. Nothing receives a batch of
  cheques: each is handed to a different person on a different day. A batch would have
  been a container whose rows all had to be worked individually anyway, and closing it
  would have asserted a hand-over for payees whose cheques were still in the drawer.
- **Writing the cheque at `action_authorize`, when the voucher is raised.** Vouchers are
  raised by the authorisation (ADR-0006 in `disbursement_finance_kmitl`) precisely because
  nothing about them is left to decide. A cheque number is not like that: it is read off a
  piece of paper that the officer is holding, at the moment they write it.
