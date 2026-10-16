# Approval ↔ Disbursement Bridge

Links an **Approval Request** to the **Disbursement Requests** finance creates from it. The requester records only what was spent; finance authors one or more ใบขอเบิก, then closes billing ([ADR-0002](docs/adr/0002-many-finance-authored-disbursements-return-to-author.md)).

## Language

**Approval Request (AR)**:
The upstream request (`approval.request`) that reserves budget and, once its actual expenses are recorded and handed to finance, is billed into **one or more** disbursements.
_Avoid_: expense request, claim

**Disbursement Request (DR)**:
The downstream payment document (`disbursement.request`) a finance officer creates from an AR in `to_disburse`. Starts with the AR's header (reservation, budget code, dimensions) and no lines; finance enters recipients, items, amounts, banks and its payment type. Draws the reservation down when approved.
_Avoid_: bill, payment request

**Billing cap**:
The AR's recorded actual total: its non-cancelled DRs together may not exceed it. Billing less is normal.
_Avoid_: reserved amount (the budget engine's own cap), per-product cap

**Close billing (ตั้งเบิกครบแล้ว)**:
Finance declaring all DRs of an AR are created; moves the AR to `billed`. Unused reservation is returned separately (คืนจอง on the ใบจองงบประมาณ).
_Avoid_: bill (the old one-shot act of generating a single DR)

**Return (ตีกลับ — DR)**:
The verification officer sending a signed DR back because its data is wrong. The DR goes back to `draft` for **its own author** (the finance officer) to fix and resubmit; the AR is untouched.
_Avoid_: correcting the approval request in place (the superseded ADR-0001 flow), reject, cancel
