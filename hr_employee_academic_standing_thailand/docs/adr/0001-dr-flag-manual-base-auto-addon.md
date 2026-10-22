# The ดร. flag is a manual field in the base, auto-derived only by a separate add-on

The "ดร."/"Dr." component of the academic-standing title used to be derived inline:
`_compute_academic_standing_title` compared the employee's highest `education_level_id`
against `hr_employee_education_history.Q01` (ปริญญาเอก) on the fly. We split this into a
stored boolean `title_dr` that is **set by hand** on the employee form in this base
module, and moved the automatic education-history derivation into a dedicated add-on,
`hr_employee_academic_standing_thailand_dr_auto`, which overrides `title_dr` with a
stored compute. This lets the ดร. prefix be driven by policy (automatic) where wanted
while still allowing a manual override deployment, and lets the base module **drop its
dependency on `hr_employee_education_history`** entirely — it was the only thing pulling
that module in.

## Considered options

- **Keep the derivation inline in the base** — no new module, but the base stays coupled
  to education history and there is no way to set ดร. by hand (e.g. honorary cases, or
  sites that do not maintain education history).
- **Make `title_dr` auto but manually overridable** — a stored compute with an inverse,
  or a default-only set. Rejected as more surface for no asked-for benefit: the two
  sites that matter want either fully automatic (install the add-on) or fully manual
  (don't).

## Consequences

- The two modules are always installed together at KMITL. `title_dr`'s column is created
  by the base module as a plain boolean, so adding the compute in the add-on does
  **not** make Odoo back-fill existing rows — the add-on ships a `post_init_hook` that
  recomputes `title_dr` (and, in turn, `academic_standing_title`) for every employee on
  install, so existing ปริญญาเอก employees keep their "ดร." with no base migration
  needed.
- While the add-on is installed, `title_dr` is read-only: the form checkbox cannot be
  edited. Manual control is available only when the add-on is absent.
