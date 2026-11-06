Ties a loan to a ใบจองงบประมาณ (`budget.commitment`) without the loan reserving on it
(advance_payment ADR-0025, ADR-0029, ADR-0033):

- A commitment may be the loan's source itself (loan type ตามใบจองงบประมาณ), but only
  when no live ใบขออนุมัติ / ใบขอให้จัดหา draws on it — otherwise the loan must cite
  that document.
- The loan stores its commitment (`budget_commitment_id`): the source itself, or the
  source's own. It follows the source in draft and is fixed at submit.
- **ยอดยืมแล้ว**: submitted, not cancelled loans on the commitment. **วงเงินยืมคงเหลือ**
  = reserved amount − ยอดยืมแล้ว. A loan may not exceed it. Both are shown on the
  commitment, with a สัญญายืมเงิน button.
- The commitment must be reserved or partly used.
- The disbursement voucher (ใบสำคัญจ่ายเงินยืม) takes the commitment header's
  financial dimensions.

The conditions are borrowing rules (exception rules) the administrators may switch off
or change from the Exception Rules menu (ADR-0030).

Any source model with a `budget_commitment_id` field is supported; no dependency on the
source modules.
