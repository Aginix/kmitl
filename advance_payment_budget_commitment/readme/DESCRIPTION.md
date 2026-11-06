Ties a loan to the ใบจองงบประมาณ (`budget.commitment`) of its source document
(ใบขออนุมัติ / ใบขอให้จัดหา), without the loan holding a commitment of its own
(advance_payment ADR-0025, ADR-0029):

- **วงเงินยืมคงเหลือ**: the commitment's reserved amount minus every
  non-cancelled loan drawn on it. A loan may not exceed it.
- The source's commitment must be reserved or partly used.
- The disbursement voucher (ใบสำคัญจ่ายเงินยืม) takes the commitment header's
  financial dimensions and its รหัสงบประมาณ (the commitment's primary code),
  shown on the loan at รอโอนเงิน. The loan voucher opts in to
  `finance_kmitl_voucher_budget_code`, so ยืนยันส่งธนาคาร refuses it while
  ส่วนงาน, แหล่งเงิน, กองทุน, ด้าน/แผนงาน/กิจกรรม or the รหัสงบประมาณ is missing.

Both conditions are borrowing rules (exception rules) the administrators may
switch off or change from the Exception Rules menu (ADR-0030).

Any source model with a `budget_commitment_id` field is supported; no
dependency on the source modules.
