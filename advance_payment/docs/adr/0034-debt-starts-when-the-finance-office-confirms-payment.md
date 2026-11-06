# The debt starts when the finance office confirms the money reached the borrower

Status: accepted (2026-11-05 feedback review). Amends ADR-0001's "Effective Date (transfer
complete) auto-moves to in_progress".

## Context & Decision

The loan became ค้างชำระ when accounting posted the voucher's entry. That can be days
after the borrower was paid, so the debt, the contract number and the due-date clock
all started late.

- **Trigger.** The loan enters `in_progress` when its disbursement voucher's
  `finance_state` becomes `paid`. That covers ยืนยันโอนสำเร็จ on an e-payment file and
  ยืนยันจ่ายสำเร็จ on a voucher outside one. Posting no longer moves the loan.
- **Effective Date** is the voucher's วันที่จ่ายจริง (`paid_date`, finance_kmitl
  ADR-0009): the file's วันที่มีผลที่ธนาคาร, the cheque date, or the voucher date for
  cash. It is the day the borrower got the money, not the day someone pressed confirm.
- **A row taken out of the file (ตีกลับ)** never becomes paid, so its loan keeps waiting
  for transfer.
- **Withdrawing the confirmation** (`_unmark_paid`, possible only before posting) puts the
  loan back to `approved` and clears the Effective Date. The Contract Number stays, so a
  number once issued is never lost. It is refused once any clearing has been booked.

## Considered options

- *Keep posting as the trigger.* Rejected: it dates the debt by the accounting queue.
- *Date the debt by the confirm press.* Rejected: the press often comes after the bank's
  effective date.
