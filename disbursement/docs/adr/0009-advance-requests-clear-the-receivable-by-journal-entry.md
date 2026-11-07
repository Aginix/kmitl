# Requests that pay no money out clear the advance receivable by a journal entry

**Status: accepted** (`disbursement_advance_clearing`; amends the accounting consequence of
advance_payment ADR-0032)

A request that pays no money out (`pays_out` false — today เงินยืม and เงินยืม (ระบบเก่า))
books spending the borrower already paid out of a loan. It used to go through ตั้งหนี้
like every request: a vendor bill (Dr expense / Cr payable), then a payment voucher that
credited a cash or bank account. That records money leaving a second time, and it never
touches the advance receivable.

Such a request now skips the bill and the pay-out:

- **ล้างลูกหนี้ (Create Advance Clearing Entry)**, an act of the accounting desk, raises one
  entry in the clearing journal (ใบสำคัญล้างลูกหนี้เงินยืม, CAR): Dr each line's expense
  with its dimensions, and Cr the advance receivable once per borrower. The journal and
  the receivable account are set once in Settings, the same account for both payment
  types. The entry is posted through the usual move approval.
- **ยืนยันการล้างหนี้ (Confirm Advance Cleared)** confirms it once posted, like ยืนยันการตั้งหนี้.
- The settlement stage reads the entry: `billed` once it is posted, `booked` once
  confirmed. It walks back by itself when the entry is reset or cancelled, and the
  confirmation is then dropped.
- ตั้งหนี้, ยืนยันการตั้งหนี้, ตรวจจ่าย, อนุมัติจ่าย and ยืนยันจ่ายสำเร็จ do not apply to such a request.
  Advance requests take their own route of stations (work_center ADR 0005), and the
  การจ่ายเงิน tab is hidden.

## Considered options

- **Keep the bill and pay through the clearing-voucher journal (PVR).** Rejected: it
  still credits a cash-type account, not the receivable, and needs a paying account the
  borrower has no bank details for.
- **A receivable account per loan (the loan's payment type).** Rejected for now: legacy
  loans have no agreement in the system, and one account in Settings serves both.

## Consequences

- The clearing entry is linked by its own field (`advance_clearing_request_id`), not
  `disbursement_request_id`, so it never counts as a bill.
- A request with taxes cannot be cleared this way. Advance requests start untaxed.
