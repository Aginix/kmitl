# A Budget Manager may consume budget without a reservation (ตัดงบตรง)

Every normal flow consumes through a reservation (ใบจองงบประมาณ): a disbursement request
needs one before it is approved, and since ADR-0016 the ledger refuses a reserve /
obligate / consume line that belongs to no commitment. Some spending is not planned
through a reservation, though, and forcing a reserve-then-consume slip for each one is
paperwork without control value.

So a **direct consumption** is allowed as a controlled exception: a `budget.move` whose
consume lines carry no `commitment_id`.

## Decisions

1. **Budget Managers only.** Posting a direct consumption, and undoing one (reset,
   cancel, delete, editing a posted line), requires `budget.group_budget_manager`. No
   setting: the normal process stays reservation-first, and the right is the gate.
2. **Consume only.** reserve / obligate lines still come from commitment events alone;
   a manual move in those buckets cannot be posted by anyone.
3. **Pool control still applies.** A direct consumption skips the reservation, not the
   pool: its lines must carry ส่วนงาน, แหล่งเงิน, กองทุน and กิจกรรม, and their amounts,
   summed per control node, must fit Available — the same check a reservation passes
   (skipped only under `budget.allow_negative`).
4. **Usage is a bucket, not a reservation.** The dashboard, its drill-downs and
   `budget_report` count usage as the reserve / obligate / consume buckets of the
   ledger rather than "lines with a commitment", so a direct consumption shows in
   เบิกจ่าย (d) and Remaining (f) agrees with the engine. The reconciliation report
   takes direct consumptions off the old-formula side, which never knew them.

## Considered options

- **A reservation reserved and consumed in one go** — still the normal path; rejected as
  the *only* path because it adds a slip per unplanned expense.
- **A setting to turn direct consumption on** — rejected: the right already gates it,
  and a second switch is one more place for the two to disagree.
- **Let any budget user do it** — rejected: it bypasses the reservation layer, so it
  stays with the role that owns the pool.
