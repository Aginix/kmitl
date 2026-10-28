ถัวจ่าย for a ใบขอให้จัดหา (พ.1), on top of `budget_commitment_cross_charge`
(budget ADR-0020).

- **จองงบประมาณ** opens the ใบจองงบประมาณ as a dialog: a draft slip
  built from (or refreshed to) the พ.1 — ปีงบ, dimensions, primary code
  and วงเงิน = the พ.1 total, all locked. The budget committer adds ถัว
  codes, then **ยืนยันจองงบประมาณ** reserves every row and advances the
  พ.1. **ปิด** leaves a harmless draft that the next press reuses.
- **ปรับถัวจ่าย** reopens the dialog while the พ.1 is reserved, unused and
  not yet sent to e-Saraban; saving re-cuts the reservation.
- ผู้จองงบประมาณ พ.1 may write the slip's split only, and only inside
  those two windows (server-side guard, no Budget User rights).
