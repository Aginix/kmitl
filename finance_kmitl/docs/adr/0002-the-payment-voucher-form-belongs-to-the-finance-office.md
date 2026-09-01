# The payment voucher form belongs to the finance office, and closes whole

The `account.payment` form is the finance office's form. Nothing else opens it: the two
menus that reach it are theirs (`finance_kmitl/views/menuitem.xml`), and the accounting
office has no entry point to it at all — their menus, their queues and the Todo raised
at the Hand-over all land on the journal entry (`account.move`).

So from **ยืนยันพร้อมส่งธนาคาร** the whole form goes read-only, not the money side
alone. The money side is frozen because the bank was told what to do (ADR-0005 of
`disbursement_finance_kmitl`), and the booking side is not the finance office's to
correct — which leaves nothing on this form for anyone holding it to change.

This is not a retreat from the per-side lock; it is where the per-side lock is drawn.
**The side is still per field, but the surface is per form.** The booking side stays
open where the accounting maker actually works: `account.payment` `_inherits`
`account.move`, so the four dimensions, the reference and the narration on the payment
form are the very same stored columns as on the journal entry — and `accounting_kmitl`'s
move form keeps them editable while the entry is `draft`, which is exactly what a
handed-over voucher is. Closing them on the finance office's form takes nothing away
from the office that owns the books.

Before this, the money side was frozen in Python (`_check_money_side_open`) but still
offered on screen: the amount, the date, the currency and the หัวจ่าย looked editable on
a confirmed voucher and threw a `UserError` on save. A form that invites an edit it will
refuse is worse than one that says up front it is closed.

## Consequences

- **The lock is view-level only.** `MONEY_FIELDS` and `_check_money_side_open` are
  unchanged and stay money-side, deliberately: extending the Python guard to the booking
  side would reach through `_inherits` and shut the journal entry form too, which is the
  one form the accounting maker exists to use.
- **Core's `state != 'draft'` is kept wherever core already had it**, OR-ed with
  `finance_state`, so cancelling a voucher the finance office never confirmed still
  closes what core closed. It is not added where core had none: posting refuses a
  voucher the finance office has not marked paid (`account_move._post`), so `posted`
  already implies `confirmed` and needs no second leaf.
- **ประเภทธุรกรรม (`kmitl_payment_type_id`) is now correctable nowhere.** It is
  classified booking side, it decides the counterpart account, and it is the one
  booking-side field with no node on the journal entry form — it lives on
  `account.payment` only. In practice it was already out of the accounting office's
  reach, since they cannot open this form; this decision makes that plain rather than
  introducing it. **Open question:** either give it a node on the move form for the
  accounting maker, or accept that the operation type is settled before the voucher goes
  to the bank and say so.
- **The third `partner_bank_id` node** (core's "Company Bank Account", shown on money
  coming in) is closed by an `attrs` and not by `readonly="1"`, because core's own
  comment above it records that a static readonly on a field the form repeats freezes
  the sibling nodes with it — and those are the payee accounts.
- **Buttons and the chatter are not part of the lock.** ยืนยันจ่ายสำเร็จ,
  ยกเลิกการยืนยัน, the assignment presses and attaching a document all keep working on a
  confirmed voucher, as they must: the lock is about facts the bank acted on, not about
  the record being inert.

## Rejected alternatives

- **`<form edit="0">`.** Static, so it would close the form in `draft` too. Odoo 16 has
  no record-dependent form-level readonly.
- **`states=` on the field definitions**, the usual Odoo whole-document lock. Odoo binds
  `states` to the field literally named `state`, and the lock here keys on
  `finance_state`.
- **Leaving the booking-side fields open on this form** (what the code did before). It
  offers the finance office an edit that is not theirs to make, on the one form they
  hold, while the office that may make it is looking at a different form.
- **Extending `MONEY_FIELDS` to the booking side** so the lock is enforced in Python
  too. It would close the journal entry form as well, which is precisely the form the
  booking side is corrected on.
