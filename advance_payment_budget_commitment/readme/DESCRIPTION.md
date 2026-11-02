Ties a loan to the ใบจองงบประมาณ (`budget.commitment`) of its source document
(ใบขออนุมัติ / ใบขอให้จัดหา), without the loan holding a commitment of its own
(advance_payment ADR-0025, ADR-0029):

- **วงเงินยืมคงเหลือ**: the commitment's reserved amount minus every
  non-cancelled loan drawn on it. A loan may not exceed it.
- The source's commitment must be reserved or partly used.
- The disbursement voucher (ใบสำคัญจ่ายเงินยืม) takes the commitment header's
  financial dimensions.

Both conditions are borrowing rules (exception rules) the administrators may
switch off or change from the Exception Rules menu (ADR-0030).

Any source model with a `budget_commitment_id` field is supported; no
dependency on the source modules.
