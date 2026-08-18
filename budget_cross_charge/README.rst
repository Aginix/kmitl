KMITL Budgeting - Cross Charge (ถัวจ่าย)
========================================

Multi-code budget reservations (ถัวจ่าย) on ``budget.commitment``.

The core ``budget`` journey is form-first: one budget code on the header,
reserved in one click. This extension adds the minority cross-charge case
(ADR 0006 / ADR 0014 in the ``budget`` module docs):

* ``budget.account.cross_chargeable`` (ถัวจ่ายได้) — a reservation may hold
  more than one budget code only when **every** code carries this flag.
* ``budget.commitment.is_cross_charge`` (ถัวจ่าย) — a UI mode switch: in
  cross-charge mode the user types the reserve lines directly in the ledger
  grid while the slip is draft; the header account/amount mirror the lines.
* The budget reservation picker returns as a browse/edit tool on cross-charge
  slips, with **edit support**: reopening it on a slip that already has
  reserve lines seeds the filter bar and the current amounts, ready to
  correct. Editing is allowed while draft, or reserved with nothing obligated
  yet (availability is re-checked after the replacement).
