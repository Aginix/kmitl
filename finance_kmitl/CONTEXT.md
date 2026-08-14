# CONTEXT — KMITL Finance

The finance office's side of paying money out: the payment voucher, the account it is
paid from, and the file the bank is sent.

Where this context ends is the point the accounting office's begins. That boundary has
a name — the **Hand-over** — and it is documented with the phase that crosses it, in
[`disbursement_finance_kmitl/CONTEXT.md`](../disbursement_finance_kmitl/CONTEXT.md).

> Terms marked **(designed)** are settled language for work that is **not yet built** —
> see `disbursement_finance_kmitl` ADR-0005.

## Terms

- **ใบจ่ายเงิน / Payment Voucher** (`account.payment`, which _is_ an `account.move` —
  core binds them with `_inherits`, so there is one document and one row, never two).
  Held by the two offices **in turn**, not shared: the finance office prepares it, sends
  it to the bank and vouches for the outcome; the accounting office books it. A
  **รายการ**จ่ายเงิน is not one of these — that is the payee-level row on a disbursement
  request. Never call a voucher "รายการจ่ายเงิน".

- **ฝั่งเงิน / Money side** _(designed)_: the facts the bank acted on — amount, payee,
  the payee's bank account, the paying account (หัวจ่าย), currency, payment and partner
  type, journal, and the **date**. Frozen from the moment the finance office confirms
  the voucher for the bank, because from then on changing any of them makes the record
  disagree with what the bank was told to do. Not "the document is locked" — half of it
  stays open.

- **ฝั่งบันทึกบัญชี / Booking side** _(designed)_: what the accounting maker may still
  correct after the money has left — the analytic distribution (all 6 dimensions), the
  reference and description, attachments, and the operation type (ประเภทธุรกรรม) and
  with it the counterpart account. This is the side the accounting office has a maker
  step *for*; freezing it would leave the people who own the books unable to fix them.

- **`finance_state`** _(designed)_: the finance office's own lifecycle on the voucher —
  `draft → confirmed → paid` — kept apart from `state`, which belongs to the accounting
  office alone. The same separation `workflow_state` already makes on the accounting
  side: one document, one field per office, neither reading the other's.
  _Avoid_: calling it "status", or reading `state` for anything the finance office does.

- **ยืนยันพร้อมส่งธนาคาร / Confirm for the bank** _(designed)_ (`draft → confirmed`):
  the finance officer's first press. It freezes the money side, gives the voucher its
  ใบสำคัญจ่าย number, and is what makes the voucher selectable into an e-payment file —
  a file may only carry vouchers that can no longer change underneath it. It says
  nothing about approval; the accounting office has not been asked anything yet.
  _Avoid_: "Submit" (that is the accounting maker's action, on `state`).

- **ยืนยันจ่ายสำเร็จ / Confirm paid** _(designed)_ (`confirmed → paid`): the finance
  office's assertion that the money reached the payee. It is the **Hand-over**, and it
  is the only human confirmation in the whole payment stretch — the bank's result file
  never enters Odoo, so nothing else in the system knows.

- **ผลการจ่าย** (`account.payment.bank_result_status`): the outcome as the finance
  office recorded it. Historically the gate everything downstream read; `finance_state`
  takes that job _(designed)_, leaving this as one more note the finance office keeps.
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
  fact and never the accounting office's `state` _(designed)_.
- **One file debits one account**, so a file's sending account is read from the paying
  account and never from the journal — a KMITL journal is a voucher type (ใบสำคัญ) and
  holds no bank account at all.
- **Nothing here is told by a bank.** No result file is imported; every outcome in this
  context is a person's word, and the exceptions are settled outside the system.
