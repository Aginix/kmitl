# CONTEXT — KMITL Finance

The finance office's side of paying money out: the payment voucher, the account it is
paid from, and the instrument that carries the money — the file the bank is sent, or the
cheque the payee collects.

Where this context ends is the point the accounting office's begins. That boundary has a
name — the **Hand-over** — and it is documented with the phase that crosses it, in
[`disbursement_finance_kmitl/CONTEXT.md`](../disbursement_finance_kmitl/CONTEXT.md).

## Terms

- **ใบจ่ายเงิน / Payment Voucher** (`account.payment`, which _is_ an `account.move` —
  core binds them with `_inherits`, so there is one document and one row, never two).
  Held by the two offices **in turn**, not shared: the finance office prepares it, sends
  it to the bank and vouches for the outcome; the accounting office books it. A
  **รายการ**จ่ายเงิน is not one of these — that is the payee-level row on a disbursement
  request. Never call a voucher "รายการจ่ายเงิน". The **menu** that opens the list of
  them is spelled **ใบสำคัญจ่าย**, because that is what the office calls the list; a
  document is still an ใบจ่ายเงิน, and its number is still a ใบสำคัญจ่าย number.

- **ฝั่งเงิน / Money side**: the facts the bank acted on — amount, payee, the payee's
  bank account, the paying account (หัวจ่าย), currency, payment and partner type,
  journal, and the **date**. Frozen from the moment the finance office confirms the
  voucher for the bank, because from then on changing any of them makes the record
  disagree with what the bank was told to do. Not "the document is locked" — the other
  half stays open, on the accounting office's own form. The **payee's bank account** is
  the one of these that freezes later: it appears in no debit and no credit, so it stays
  correctable until the instruction actually leaves — the moment the e-payment file
  carrying it is exported, or, for a voucher settled by cheque or cash,
  ยืนยันจ่ายสำเร็จ. Since the voucher form itself closes whole at confirmation
  (ADR-0002), the correction is made on the row in the e-payment file, which is where an
  officer assembling the file would notice a wrong account in the first place. See
  [ADR-0003](./docs/adr/0003-the-payees-bank-account-freezes-when-the-file-leaves.md).

- **ฝั่งบันทึกบัญชี / Booking side**: what the accounting maker may still correct after
  the money has left — the analytic distribution (all 6 dimensions), the reference and
  description, attachments, and the operation type (ประเภทธุรกรรม) and with it the
  counterpart account. This is the side the accounting office has a maker step _for_;
  freezing it would leave the people who own the books unable to fix them. It is
  corrected on the **journal entry**, not here: `account.payment` `_inherits`
  `account.move`, so these are the same stored columns seen from the other office's form
  ([ADR-0002](./docs/adr/0002-the-payment-voucher-form-belongs-to-the-finance-office.md)).

- **`finance_state`**: the finance office's own lifecycle on the voucher —
  `draft → confirmed → paid` — kept apart from `state`, which belongs to the accounting
  office alone. The same separation `workflow_state` already makes on the accounting
  side: one document, one field per office, neither reading the other's. _Avoid_:
  calling it "status", or reading `state` for anything the finance office does.

- **ยืนยันพร้อมส่งธนาคาร / Confirm for the bank** (`draft → confirmed`): what makes a
  voucher fit to be sent — it freezes the money side, gives the voucher its ใบสำคัญจ่าย
  number, and is what makes it selectable into an e-payment file, because a file may
  only carry vouchers that can no longer change underneath it. It says nothing about
  approval; the accounting office has not been asked anything yet. A voucher on a
  disbursement request is confirmed by the **authorisation** that raised it, not by a
  press of the finance office's — theirs is a press only on a voucher they filled in by
  hand, or one they took back to correct with **ยกเลิกการยืนยัน**. _Avoid_: calling it
  "the finance officer's first press" (it is not, for a voucher that came from a
  request), or "Submit" (that is the accounting maker's action, on `state`).

- **วันที่บนใบสำคัญจ่าย / Voucher date** (`account.payment.date`): the day the voucher
  was raised — for a disbursement, the day it was authorised. It is money side and it
  never moves, because it is both the accounting period and what numbers the voucher:
  ใบสำคัญจ่าย runs `PV/2026/00001`, year-reset, so a date in another year and a number
  already issued cannot both be true — and a date moved even within the year would move
  an accounting period the finance office does not own. It is _not_ a claim about when
  the money left; that is the effective date below. _Avoid_: reading it as the payment
  date.

- **วันที่มีผลที่ธนาคาร / Effective date** (`bank.payment.export.effective_date`): the
  day the bank moves the money — the one record of when the payee was actually paid,
  because it is what the bank was told to act on. The **withholding-tax certificate is
  dated from it** (ภ.ง.ด.3/53 is filed by the 7th of the month following the month of
  payment, so the certificate has to say the day the income was paid), while the voucher
  and its entry keep the voucher date. The two agree except when a file leaves in a
  later month than the authorisation, and there they are deliberately allowed to differ
  — see `disbursement_finance_kmitl` ADR-0006.

- **ยืนยันจ่ายสำเร็จ / Confirm paid** (`confirmed → paid`): the finance office's
  assertion that the money reached the payee. It is the **Hand-over**, and it is the
  only human confirmation in the whole payment stretch — the bank's result file never
  enters Odoo, so nothing else in the system knows. Each way of paying makes it in the
  place that knows: a transfer when its **ไฟล์ e-Payment** is closed, a cheque when the
  cheque is **มอบ**, and cash on the voucher itself, which is what the press of that
  name is left for. _Avoid_: reading it as one button on the voucher — for two of the
  three it is not.

- **เช็คจ่าย / Cheque** (`cheque.register`): one cheque, written for one voucher. What
  the **ไฟล์ e-Payment** is to a transfer, this is to a cheque — the thing that stands
  between the voucher being confirmed and the voucher being paid, and that carries what
  the office does in between. The difference is arity: a file is one instruction to one
  bank covering many payees, so it holds payees, amounts and dates of its own; a cheque
  covers one payee, so it holds none of them and reads them off the voucher. What is its
  own is the paper — the number, the book, the date on it, and whether it was printed,
  collected, or died. See
  [ADR-0006](./docs/adr/0006-a-cheque-is-the-e-payment-file-of-one-voucher.md). _Avoid_:
  "ทะเบียนคุมเช็ค" for a single cheque — that names the list, not the document.

- **เล่มเช็ค / Cheque book** (`account.payment.method.line.bank_account_id`): the
  institute's own bank account a cheque is drawn on. Cheque numbers run without
  repeating **within one book** and mean nothing across books, so the book is what
  scopes both the uniqueness of a number and the guess at the next one. _Avoid_:
  `account.journal` — a journal is a **ใบสำคัญ**, a document type, and holds no bank
  account at all (ADR-0001).

- **เลขที่เช็ค / Cheque number**: read off the pre-printed paper, never issued by Odoo.
  What the system offers is a **guess** — one past the highest already spent in the same
  book — and a guess that is wrong is overtyped. Nothing counts and nothing is reserved,
  which is why a page torn out and thrown away needs no record: it costs the next guess
  one keystroke. _Avoid_: calling it a sequence.

- **ออกเช็ค / Issue** (`draft → issued`): the paper now exists, with its number and its
  date on it. It says nothing about who has it. _Avoid_: reading it as payment.

- **มอบเช็ค / Hand over** (`issued → paid`): the payee has the cheque, so the money has
  reached them. This is the **Hand-over** for a cheque payee, and it is what closing an
  e-payment file is for a transfer payee.

- **วันที่บนเช็ค / Cheque date** (`cheque.register.cheque_date`): the day the payee may
  present the cheque, which is the day the Revenue Department treats the income as paid
  — so the **withholding-tax certificate is dated from it**, exactly as it is dated from
  an e-payment file's effective date for a transfer. Frozen once the cheque is issued,
  because it is printed on paper this system no longer controls. _Avoid_: confusing it
  with the handover date, which has no tax effect at all: a cheque dated the 25th and
  collected on the 30th is September's withholding either way.

- **ยกเลิกเช็ค / Cancel a cheque** (`→ cancelled`): the paper is dead and this number
  will never pay anyone. Bounced, lost, uncashed until it went out of date, drawn wrong,
  spoiled in the printer — one state and a reason beside it, because to the register
  every death is the same fact. The number stays spent. A cheque that had already been
  handed over takes its voucher back to `confirmed` with it, and a replacement is
  written on that **same** voucher: only the instrument died, not the obligation. See
  [ADR-0007](./docs/adr/0007-a-dead-cheque-takes-its-voucher-back.md).

- **ประเภทผู้รับเงิน / Payee type** (`account.payment.payee_type_id` →
  `res.partner.type`): what kind of counterparty the payee is — the category that
  carries their default payable account and their withholding-tax rate. It is **not**
  core's `partner_type` (`customer` / `supplier`), which says which side of the ledger
  the voucher is on and nothing about who is being paid. Both live on `account.payment`,
  which is exactly why this one is not called `partner_type_id` the way it is on
  `res.partner` and on `finance.assignment.rule` — on those models there is nothing for
  it to collide with. _Avoid_: "partner type" unqualified, on a payment.

- **ภาษีหัก ณ ที่จ่ายบนใบจ่ายเงิน** (`account.payment.wht_tax_id`, `wht_amount_base`,
  `wht_cert_income_type`): what a voucher the finance office **filled in by hand**
  withholds. Three facts, and they do not all fall on the same side: the rate and the
  **ฐานเงินได้** are money side, because between them they decide what the bank was told
  to pay; the **ประเภทเงินได้** is not — it moves no entry and appears in no
  instruction, being what the certificate is _about_. A voucher raised from a
  disbursement has none of the three: its withholding was settled on the bill and
  reached the entry as a line, and a rate here as well would withhold the payee twice.
  That is why the rate is proposed by an **onchange** from the payee's ประเภทผู้รับเงิน
  and never by a compute — a voucher another document raises is created in Python, where
  no onchange runs, so the mistake is not guarded against so much as unreachable.
  _Avoid_: reading `amount_wht` as an input; it is worked out from these.

- **ฐานเงินได้ / Withholding base** (`account.payment.wht_amount_base`): the income the
  rate is applied to. On a hand-filled voucher it is **what the officer typed into the
  amount box** — because the figure they have is the one on the invoice in their hand,
  not the smaller one that will leave the bank. The amount box then shows the amount
  paid and closes: it holds a derived figure from that moment, and typing over a derived
  figure would withhold from a net already withheld from. Correcting a mistyped income
  therefore means **clearing the rate**, which hands the withholding back and opens the
  box again. KMITL charges no VAT and a voucher withholds one thing, so the base is the
  whole of what is owed. _Avoid_: "ยอดเต็ม", and avoid calling it a field the office
  fills in — they fill in the amount, and this is what that means.

- **ยอดก่อนหัก ณ ที่จ่าย** (`account.payment.amount_before_wht`): the gross the payee is
  owed, **read back** as the amount paid plus what was withheld from it. Never typed and
  never stored: on a hand-filled voucher the typed figure is the base and this equals
  it, and on a voucher raised from a disbursement both halves were settled with the
  bill. One number, arrived at from whichever end filled the document in, which is why
  the form shows the base on the one and this on the other and never both.

- **หนังสือรับรองการหักภาษี ณ ที่จ่าย / WHT certificate** (`withholding.tax.cert`): the
  50 ทวิ the payee files with the Revenue Department — **and the record KMITL files its
  own ภ.ง.ด. from**, because the institute gathers and submits the withholding itself
  rather than leaving it to a bank. That is what makes it more than a courtesy copy: a
  payee with no certificate, or with one still in draft, is a payee **missing from the
  return**. It is the **voucher's**, not the journal entry's — created with `payment_id`
  and no `move_id` — because the paper goes out with the money, weeks before the
  accounting office books the voucher, and because posting an entry deletes every
  certificate hanging off it. It is dated from the day the money actually left (the
  e-payment file's effective date, or the date on the cheque) rather than the voucher's
  own date, so it falls in the month it is filed in. See
  [ADR-0008](./docs/adr/0008-the-wht-certificate-belongs-to-the-voucher.md) and
  [ADR-0009](./docs/adr/0009-the-certificate-is-raised-by-the-payment.md). _Avoid_:
  calling it a ภ.ง.ด. — that is the monthly return, footed from these; and avoid reading
  it as something an officer decides to produce (below).

- **การยกหนังสือรับรอง / Raising the certificate**: it is **the Hand-over that raises
  it**, not a press of anybody's — one per payee that withheld, made the moment the
  money reaches them, which is also the day the law dates the withholding from. Each way
  of paying does it in the place that knows: closing an **ไฟล์ e-Payment** raises them
  for every transfer payee it carried, **มอบเช็ค** for that cheque's payee, and
  ยืนยันจ่ายสำเร็จ for cash. The press that remains on the voucher is for the ones the
  Hand-over could not write — a rate naming no type of income, a certificate cancelled
  and needing a successor. A certificate that cannot be written **does not stop the
  Hand-over**: the money reached the payee, and no document may contradict that; the
  reason goes in the chatter. See
  [ADR-0009](./docs/adr/0009-the-certificate-is-raised-by-the-payment.md). _Avoid_:
  "ออกหนังสือรับรอง" as the name of a step in the payment run — there is no such step.

- **การรวบรวมนำส่ง / The filing run** (`withholding.tax.cert.state`, `draft → done`):
  the finance office's monthly pass over a month's certificates — footed, checked, and
  confirmed in one press. Confirming is not a formality: the ภ.ง.ด. report reads only
  certificates that are **no longer draft**, so this is the act that puts a month in the
  return, and a certificate left in draft is a payee left out of it. This is why
  certificates are raised as drafts rather than finished: the review that matters
  happens once a month over the whole return, not once per voucher at the counter.
  _Avoid_: reading `done` as "printed" or "handed to the payee" — the paper goes out at
  the Hand-over, long before the month is filed.

- **ผลการจ่าย** (`account.payment.bank_result_status`): the outcome as the finance
  office recorded it. Historically the gate everything downstream read; `finance_state`
  takes that job, leaving this as one more note the finance office keeps. _Avoid_
  reading it as "what the bank reported": nothing here is told by a bank.

- **ไฟล์ e-Payment** (`bank.payment.export`): one file, uploaded to one bank, debiting
  **one** paying account — which is why the paying account is chosen on the file first
  and the vouchers that may be picked into it are narrowed to the ones paid from it. A
  request whose payees span four paying accounts produces four files. _Avoid_:
  "ส่งออกรายการจ่ายเงิน" — it steps on **รายการจ่ายเงิน**, which names the row on a
  disbursement request. Also avoid "PE": that is the prefix its number happens to carry,
  not a name for the thing. The **menu** is **ทะเบียน e-Payment**: the register is the
  list, a file is one record in it — the same pair as ทะเบียนคุมเช็ค and a cheque.

- **สถานะของไฟล์ e-Payment** (`bank.payment.export.state`), and what each one actually
  claims — the distinction matters because none of them is told by a bank:

  - **ร่าง** (`draft`) — being assembled. The only state a file can be deleted in.
  - **ยืนยันแล้ว** (`confirm`) — the rows are settled and the file is fit to produce.
  - **ออกไฟล์แล้ว** (`done`) — the file has been generated and kept. It says nothing
    about whether anyone has uploaded it yet, which is why the per-row ผลการจ่าย exists.
  - **จ่ายสำเร็จ** (`paid`) — a person has confirmed the money reached the payees, and
    the file is closed. The last state, not `done` — see
    [ADR-0004](./docs/adr/0004-done-is-not-the-last-state-of-an-e-payment-file.md).
  - **ยกเลิก** (`cancel`) — abandoned before it was produced.
  - **ตีกลับ** (`reject`) — produced, then found unusable. Both release every voucher in
    the file back to being pickable. _Avoid_: reading `done` as "ส่งธนาคารแล้ว". The
    system never observes the upload.

- **แถวในไฟล์ e-Payment** (`bank.payment.export.line`): one voucher's row in one file.
  It carries what the bank was told — `sending_acc_number` and the payee's account. It
  also holds a per-row result (`epayment_status`, `epayment_ref`, `epayment_note`),
  which is what a voucher's **ผลการจ่าย** is read from, but the office does not work a
  file row by row and those are out of the way in the UI: the result is recorded once,
  on the file.

- **การยืนยันการโอนเงิน** (`bank.payment.export` → `paid`): one press for the whole
  file, saying every payee has their money. Not a claim that the bank managed it — a
  payee it could not credit was chased and settled outside the system first, and the
  press covers them too. What that press carries is therefore the exception, in two
  parts: **หลักฐานการโอนเงิน** (`transfer_proof_ids`), what the bank sent back, which is
  required before the file may close and is kept apart from the exported file so the two
  are never mistaken for each other; and the **note** (`epayment_note`), asked for at
  the moment of the press because that is the only moment anyone knows it. This note
  **stays with the finance office**: the accounting office never opens an e-payment
  file.

- **หัวจ่าย / Paying Account** (`account.payment.method.line`): out of which bank
  account the money leaves, by which means, under which voucher, against which GL
  account — one of Odoo's own records rather than a model of our own. See
  [ADR-0001](./docs/adr/0001-paying-account-is-a-payment-method-line.md).

## Rules

- **A voucher may enter an e-payment file only once it can no longer change.** That is
  what confirming it for the bank buys, and it is why the file's gate is a finance-side
  fact and never the accounting office's `state`.
- **The voucher form is the finance office's, and it closes whole when they confirm.**
  Nothing else opens it, so once the money side is frozen there is nothing left on it
  for the holder to change — and a form that offers an edit it will refuse on save is
  worse than one that says up front it is closed. The booking side is corrected on the
  journal entry. Note ประเภทธุรกรรม has no node there yet (ADR-0002).
- **One file debits one account**, so a file's sending account is read from the paying
  account and never from the journal — a KMITL journal is a voucher type (ใบสำคัญ) and
  holds no bank account at all.
- **Nothing here is told by a bank.** No result file is imported; every outcome in this
  context is a person's word, and the exceptions are settled outside the system. This is
  also why nothing here follows a cheque after it is handed over: which cheques are
  still outstanding is a line in the **bank reconciliation**, and that is the accounting
  office's paper.
- **A cheque number, once spent, is never handed to a second payee.** A cancelled cheque
  keeps the number it was torn off with, which is why cancelling one leaves its row
  behind and why a voucher can end up with several — at most one of them not cancelled.
- **The way back exists only for a cheque, and only while the entry is unposted.** The
  phase is otherwise forward-only. A cheque is the one instrument that can fail after
  the payee is holding it, so its death withdraws the assertion that they were paid
  instead of being corrected downstream. Once the accounting office has posted, the
  money has left the books too, and only their reversal can undo it (ADR-0007).
- **Naming a dimension names everything under it.** A voucher filtered by a faculty, a
  fund or a programme is any voucher on that account _or on any account beneath it_.
  This is the same reading the routing rules use to decide who carries a voucher
  (`finance.assignment.rule`), and it has to stay the same reading: a rule set on a
  faculty that routes a department's vouchers, beside a list filter on that faculty that
  finds none of them, would be one word meaning two things.
- **A payee is withheld from in exactly one place.** A voucher either says what it
  withholds — filled in on the voucher itself, in the Finance app — or carries a
  withholding decided on the bill it pays, which reaches its entry as a line. Never
  both: the entry is built from whichever of the two applies, and nothing merges them.
  This is a rule that is hard to break rather than one that is checked, because the rate
  on the voucher is only ever set by hand on the form.
- **A ใบสำคัญจ่าย number, once issued, never changes** — and because Odoo binds the
  number to the voucher's date, that pins the date with it. Anything that has to say
  when the money actually left says it with the e-payment file's effective date instead
  of by moving the voucher.
