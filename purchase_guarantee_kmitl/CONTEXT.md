# Purchase Guarantee

Security deposits (หลักประกัน) a supplier lodges with KMITL to back a bid or a
contract: what form they take, what they are held against, and — for the ones
that are actually money — how that money is received and returned.

## Language

**Guarantee** (หลักประกัน):
The `purchase.guarantee` record. Numbered `PG…`, raised by the procurement
officer (พัสดุ) against a Purchase Request, a Purchase Agreement or a Purchase
Order, and carrying the four financial dimensions of the document it backs.
_Avoid_: Bond, Warranty, Retention (เงินประกันผลงาน is a different thing —
`kris_project` withholds it per installment and never creates a
`purchase.guarantee`).

**Guarantee Kind** (ประเภทหลักประกัน):
*What the guarantee is held against* — `purchase.guarantee.method`. KMITL uses
two: **หลักประกันการเสนอราคา** (a bid, raised from a Purchase Request) and
**หลักประกันสัญญา** (a contract, raised from a Purchase Order). It carries the
GL account the money is held on, so each kind can sit on its own deposit
liability.
**The English and the Thai are crossed here**: the model is called `method` but
the word for it is *ประเภท*. _Avoid_: วิธีการ, Method (in Thai prose).

**Guarantee Form** (รูปแบบหลักประกัน):
*What the supplier actually lodged* — `purchase.guarantee.type`. KMITL uses two:
**เงินสด/เงินโอน** and **หนังสือค้ำประกันออกโดยธนาคาร**.
**The English and the Thai are crossed here too**: the model is called `type`
but the word for it is *รูปแบบ*. _Avoid_: ประเภท (that is the Guarantee Kind).

**Monetary guarantee** (หลักประกันที่รับเป็นตัวเงิน):
A Guarantee Form KMITL actually holds the money for (`is_monetary`). Only these
are receipted and booked; a bank guarantee letter is a promise, so it is
recorded and watched for expiry but never touches the ledger. One guarantee is
received once and returned once.
_Avoid_: `is_create_invoice` — the upstream module's flag, which drove an
invoice route KMITL never used. It is hidden from the configuration form and
means nothing here.

**Guarantee account** (บัญชีเงินหลักประกัน):
The deposit liability a Guarantee Kind's money is held on
(`purchase.guarantee.method.account_id`), configured by the treasury office in
Purchase ▸ Configuration ▸ Guarantee Method. It is the single source: both the
receipt line and the return request's line are stamped from it, never from the
เงินหลักประกัน product, whose own accounts are only a fallback.

**Guarantee Receipt** (ใบเสร็จรับเงินหลักประกัน):
The document issued when a monetary guarantee's money arrives — a `kmitl.receipt`
of kind *Guarantee*, numbered `RG/<ปีงบ>/nnnn` in its own register. A different
document from the revenue ใบเสร็จรับเงิน, sharing its model and its remittance
workflow. See [receipt_kmitl](../receipt_kmitl/CONTEXT.md).
_Avoid_: ใบส่งเงิน (the old `account.payment` route's name for it — removed).

**Return request** (ใบขอเบิกคืนหลักประกัน):
The `disbursement.request` that sends a monetary guarantee's money back, raised
from the guarantee itself and pointing at it through `reference`. It consumes no
budget — the money was never the institute's. See
[purchase_guarantee_disbursement](../purchase_guarantee_disbursement/docs/adr/0001-a-guarantee-is-returned-through-a-disbursement.md).
_Avoid_: Refund, ตีกลับ (ตีกลับ is returning a *document* for correction).

**Lock**:
The state a guarantee moves to when its receipt is issued (`draft` → `lock`).
It freezes every field, including the due date and the attachments, so a
contract extension is recorded by resetting to draft first. Cancelling the
receipt does **not** unlock it — a chatter note says so and leaves the decision
to a person.

## Known limitations (accepted, revisit later)

- **Forfeiture is not modelled.** When a supplier defaults and KMITL keeps the
  deposit, there is no route that clears the deposit liability to income — the
  treasury office raises the journal entry by hand. The guarantee itself just
  never gets a return request.
- **Expiry reminders stop once the money is received.**
  `purchase_guarantee_expiration` only notifies on guarantees in `draft`, and
  issuing a receipt locks the guarantee — so the ones KMITL is actually holding
  money for are the ones it stops reminding about. (That module is not in
  `kmitl_depends_dev` today.) The fix is to key the cron off `date_return`
  rather than `state`.
- **A guarantee's dimensions are whatever its source document's lines merge to.**
  `_compute_analytic` folds every line of the Purchase Order or Requisition into
  one distribution, so a document spanning two departments silently keeps the
  last one — and that is the department the receipt is filed under.
