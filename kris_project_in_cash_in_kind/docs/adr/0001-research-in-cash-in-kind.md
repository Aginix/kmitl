# Research projects split Project Value into In Cash + In Kind

Research contracts routinely bundle actual cash the university receives with **in-kind**
matching contributions (equipment, staff time, materials from the client or a partner)
that never flow through KRIS's cash accounts. Before this add-on existed, `project_value`
in `kris_project` was one number, so KRIS was (a) deducting the institutional
maintenance fee on money it never received and (b) reporting `revenue_remaining` that
could never reach 0 whenever any in-kind portion existed. This add-on inherits
`kris.project` and, on projects whose category is the seed record
`kris_project.project_category_research`, turns `project_value` into a stored derivation
of `in_cash + in_kind`. Every cash-flow computation (`operating_expense`,
`maintenance_deduction_amount`, `revenue_remaining`, `warn_installment_total_mismatch`)
anchors on a new stored compute `cash_target` that returns `in_cash` for research and
`project_value` for everything else. Non-research projects retain the pre-existing
behaviour untouched — the new fields are hidden and the compute is a no-op — because
academic-service contracts have no in-kind concept in KRIS's business.

## Considered options

**Ship as an add-on module vs. edit `kris_project` directly.** An earlier iteration
shipped the change inside `kris_project`; it was refactored into this add-on so the base
module stays untouched, the feature is opt-in per deployment, and uninstalling the
add-on cleanly reverts the field-redefinition and drops the columns.

**Gating by xmlid vs. a `is_research` flag on `kris.project.category`.** We chose xmlid
lookup (`env.ref("kris_project.project_category_research", raise_if_not_found=False)`)
because the two seed categories (งานบริการวิชาการ / งานวิจัย) are stable business
concepts, other modules in this repo already gate on seed records (operating unit `99`),
and the cost of migrating to a per-category flag later is low if a second
in-kind-bearing category ever appears. The `raise_if_not_found=False` fallback degrades
gracefully to "not research" so a deleted seed record does not break the module.

**`in_cash` as the cash anchor vs. tracking in-kind receipts.** We could have kept
`project_value` as the anchor and modelled in-kind as its own receipt stream so the
existing comparisons stayed correct. Rejected: KRIS never records in-kind contributions
as receipts (there is no cash movement to record); the simpler split — total value
displayed as `in_cash + in_kind`, all cash logic anchored on `in_cash` — matches the
existing receipt/installment semantics exactly.
