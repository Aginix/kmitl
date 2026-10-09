# A supported project opens its analytic to every unit

A project's `kmitl_project` analytic account is minted scoped to the project's operating
unit, so only the owning unit can see (and therefore pick) it. KMITL needs **another
unit** to be able to fund a project through a budget transfer — unit B transferring its
own money into unit A's project. We add a Boolean **มีการสนับสนุนจากหน่วยงานอื่น**
(`is_supported_by_other_units`) on `kmitl.project`, delivered by the bridge
`kmitl_project_budget_transfer`.

## Decisions

1. **The flag clears the analytic's operating units — system-wide.** Ticked → the
   project's analytic gets `operating_unit_ids = False` (visible to every unit).
   Unticked → restored to the project's own OU. Ticking it in draft (no analytic yet)
   applies when the analytic is minted at ส่งเข้าแผน. Editable in every state (a
   supporter may appear after จองงบ, e.g. a top-up).
2. **The TO line lands on the project's own coordinate.** The supporting unit types the
   owning unit's ส่วนงาน/กิจกรรม/กองทุน on the TO line; nothing is auto-filled. The
   budget engine, the computed `budget_amount` (ADR-0006, full-coordinate) and the
   exception rule `budget_transfer_check_kmitl_project_source` are unchanged.
3. **The transfer-line picker narrows progressively** to projects matching the line's
   รหัสงบ, ปีงบ, and the dimensions already set (blank ones don't filter; project state
   doesn't filter, so a cancelled project stays pickable on FROM to pull money back).
   The OU filter of the analytic picker then hides other units' _unflagged_ projects.

## Considered options

- **Picker-only bypass** (`all_analytic_ou` context on the transfer line's project
  field, filtered to flagged projects). Keeps other pickers unaffected but needs a
  hand-built OU domain on the transfer line and leaves the analytic's own visibility
  saying "owner only" while other units post against it. Rejected in favour of making
  the data say what is true.
- **Supporter-coordinate TO** (money lands at ส่วนงาน B + project tag). Breaks
  ADR-0006's full-coordinate `budget_amount` and the source-match exception rule.
  Rejected.
- **A list of supporting units** instead of a Boolean. More precise but needs upkeep;
  not needed now.

## Consequences

- A flagged project's analytic also appears in other units' analytic pickers elsewhere
  (purchase requests, disbursements). Accepted — those pickers have their own domains
  and the project's exception rules still guard mismatches.
- Unflagging later does not touch already-posted transfers; it only hides the project
  from new picks.
