ถัวจ่าย (cross-charge): one ใบจองงบประมาณ reserved across several budget
codes at the same dimensions (budget ADR-0020).

- Adds the **รายการจองงบประมาณ** (Reservation Split) grid to the
  reservation form. Row ★ is the primary code (the header `account_id`);
  its amount is always the วงเงิน minus the ถัว rows.
- ถัว codes must be ticked **ถัวจ่ายได้** (`cross_chargeable`) and funded at
  the reservation's dimensions.
- จองงบ posts one reserve event per row, primary first (budget ADR-0018
  order). A reserved, unused split can be re-cut: its reserve events are
  cancelled and reposted after a per-pool re-check.
- Standalone slips use the split while draft; project and plan slips
  stay single-code. Owners widen the edit window (see
  `purchase_request_budget_cross_charge`).
