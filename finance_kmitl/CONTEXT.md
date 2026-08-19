# CONTEXT — KMITL Finance

The finance office's side of paying money out: the payment voucher, the account it is
paid from, and the file the bank is sent.

Where this context ends is the point the accounting office's begins. That boundary has
a name — the **Hand-over** — and it is documented with the phase that crosses it, in
[`disbursement_finance_kmitl/CONTEXT.md`](../disbursement_finance_kmitl/CONTEXT.md).

## Terms

- **ใบจ่ายเงิน / Payment Voucher** (`account.payment`, which _is_ an `account.move` —
  core binds them with `_inherits`, so there is one document and one row, never two).
  Held by the two offices **in turn**, not shared: the finance office prepares it, sends
  it to the bank and vouches for the outcome; the accounting office books it. A
  **รายการ**จ่ายเงิน is not one of these — that is the payee-level row on a disbursement
  request. Never call a voucher "รายการจ่ายเงิน".

- **ฝั่งเงิน / Money side**: the facts the bank acted on — amount, payee,
  the payee's bank account, the paying account (หัวจ่าย), currency, payment and partner
  type, journal, and the **date**. Frozen from the moment the finance office confirms
  the voucher for the bank, because from then on changing any of them makes the record
  disagree with what the bank was told to do. Not "the document is locked" — the other
  half stays open, on the accounting office's own form.

- **ฝั่งบันทึกบัญชี / Booking side**: what the accounting maker may still
  correct after the money has left — the analytic distribution (all 6 dimensions), the
  reference and description, attachments, and the operation type (ประเภทธุรกรรม) and
  with it the counterpart account. This is the side the accounting office has a maker
  step *for*; freezing it would leave the people who own the books unable to fix them.
  It is corrected on the **journal entry**, not here: `account.payment` `_inherits`
  `account.move`, so these are the same stored columns seen from the other office's
  form ([ADR-0002](./docs/adr/0002-the-payment-voucher-form-belongs-to-the-finance-office.md)).

- **`finance_state`**: the finance office's own lifecycle on the voucher —
  `draft → confirmed → paid` — kept apart from `state`, which belongs to the accounting
  office alone. The same separation `workflow_state` already makes on the accounting
  side: one document, one field per office, neither reading the other's.
  _Avoid_: calling it "status", or reading `state` for anything the finance office does.

- **ยืนยันพร้อมส่งธนาคาร / Confirm for the bank** (`draft → confirmed`):
  what makes a voucher fit to be sent — it freezes the money side, gives the voucher its
  ใบสำคัญจ่าย number, and is what makes it selectable into an e-payment file, because a
  file may only carry vouchers that can no longer change underneath it. It says nothing
  about approval; the accounting office has not been asked anything yet. A voucher on a
  disbursement request is confirmed by the **authorisation** that raised it, not by a
  press of the finance office's — theirs is a press only on a voucher they filled in by
  hand, or one they took back to correct with **ยกเลิกการยืนยัน**.
  _Avoid_: calling it "the finance officer's first press" (it is not, for a voucher that
  came from a request), or "Submit" (that is the accounting maker's action, on `state`).

- **วันที่บนใบสำคัญจ่าย / Voucher date** (`account.payment.date`): the day the voucher
  was raised — for a disbursement, the day it was authorised. It is money side and it
  never moves, because it is both the accounting period and what numbers the voucher:
  ใบสำคัญจ่าย runs `PV/2026/00001`, year-reset, so a date in another year and a number
  already issued cannot both be true — and a date moved even within the year would move
  an accounting period the finance office does not own. It is _not_ a claim about when
  the money left; that is the effective date below.
  _Avoid_: reading it as the payment date.

- **วันที่มีผลที่ธนาคาร / Effective date** (`bank.payment.export.effective_date`): the
  day the bank moves the money — the one record of when the payee was actually paid,
  because it is what the bank was told to act on. The **withholding-tax certificate is
  dated from it** (ภ.ง.ด.3/53 is filed by the 7th of the month following the month of
  payment, so the certificate has to say the day the income was paid), while the voucher
  and its entry keep the voucher date. The two agree except when a file leaves in a
  later month than the authorisation, and there they are deliberately allowed to differ
  — see `disbursement_finance_kmitl` ADR-0006.

- **ยืนยันจ่ายสำเร็จ / Confirm paid** (`confirmed → paid`): the finance
  office's assertion that the money reached the payee. It is the **Hand-over**, and it
  is the only human confirmation in the whole payment stretch — the bank's result file
  never enters Odoo, so nothing else in the system knows.

- **ประเภทผู้รับเงิน / Payee type** (`account.payment.payee_type_id` → `res.partner.type`):
  what kind of counterparty the payee is — the category that carries their default
  payable account and their withholding-tax rate. It is **not** core's `partner_type`
  (`customer` / `supplier`), which says which side of the ledger the voucher is on and
  nothing about who is being paid. Both live on `account.payment`, which is exactly why
  this one is not called `partner_type_id` the way it is on `res.partner` and on
  `finance.assignment.rule` — on those models there is nothing for it to collide with.
  _Avoid_: "partner type" unqualified, on a payment.

- **ผลการจ่าย** (`account.payment.bank_result_status`): the outcome as the finance
  office recorded it. Historically the gate everything downstream read; `finance_state`
  takes that job, leaving this as one more note the finance office keeps.
  _Avoid_ reading it as "what the bank reported": nothing here is told by a bank.

- **ไฟล์ e-Payment** (`bank.payment.export`): one file, uploaded to one bank, debiting
  **one** paying account — which is why the paying account is chosen on the file first
  and the vouchers that may be picked into it are narrowed to the ones paid from it. A
  request whose payees span four paying accounts produces four files.
  _Avoid_: "ส่งออกรายการจ่ายเงิน" — it steps on **รายการจ่ายเงิน**, which names the row
  on a disbursement request.

- **แถวในไฟล์ e-Payment** (`bank.payment.export.line`): one voucher's row in one file.
  It carries what the bank was told (`sending_acc_number`, the payee's account) and what
  the officer noted afterwards (`epayment_status`, `epayment_ref`, `epayment_note`) —
  including how a payee the bank rejected was settled outside the system. This note
  **stays with the finance office**: the accounting office never opens an e-payment file.

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
  context is a person's word, and the exceptions are settled outside the system.
- **Naming a dimension names everything under it.** A voucher filtered by a faculty,
  a fund or a programme is any voucher on that account _or on any account beneath it_.
  This is the same reading the routing rules use to decide who carries a voucher
  (`finance.assignment.rule`), and it has to stay the same reading: a rule set on a
  faculty that routes a department's vouchers, beside a list filter on that faculty
  that finds none of them, would be one word meaning two things.
- **A ใบสำคัญจ่าย number, once issued, never changes** — and because Odoo binds the
  number to the voucher's date, that pins the date with it. Anything that has to say
  when the money actually left says it with the e-payment file's effective date instead
  of by moving the voucher.
