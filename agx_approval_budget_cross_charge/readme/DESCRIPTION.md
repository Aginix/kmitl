ถัวจ่าย for a คำขออนุมัติค่าใช้จ่าย (`approval.request`), on top of
`budget_commitment_cross_charge` (agx_approval ADR-0011, budget ADR-0020).

- **ยืนยันงบประมาณ** opens the ใบจองงบประมาณ as a dialog: a draft slip
  built from (or refreshed to) the request — ปีงบ, dimensions, primary code
  and วงเงิน = the request total (locked). The Budget Confirmer adds ถัว
  codes (flagged ถัวจ่ายได้ **and** usable from a คำขออนุมัติ), may change the
  primary code or dimensions, then **ยืนยันจองงบประมาณ** reserves every row
  and sends the request on. **ปิด** leaves a harmless draft that the next
  press reuses.
- **แก้ไขใบจอง** reopens the dialog while the request is reserved and unused,
  at รอส่งขออนุมัติ or back from e-Saraban (ตีกลับ/ดึงกลับ). Saving re-cuts
  the reservation in one step and copies a changed code or dimension back
  to the request.
- The approval letter lists every code with its amount.
