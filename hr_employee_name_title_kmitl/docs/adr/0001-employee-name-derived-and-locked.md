# Employee name is a derived, locked value — not a two-way name/parts field

`kmitl_hr_employee_full_name` keeps `hr.employee.name` and the `firstname`/`middlename`/
`lastname` parts in **two-way** sync: typing parts builds the name, and writing a bare
name splits it back into parts (`_inverse_name` / the reverse branch of the create/write
prepare helpers). This module makes the name carry a work-track **title prefix**
(academic standing title, or the personal honorific `prefix_id`), which breaks that
symmetry: once `name` is "ศาสตราจารย์ ดร.สมชาย ใจดี", splitting it back would push the
title into `firstname`. So we make the name a **one-way derived, locked** value instead.
We keep `name` as core's related-to-`resource_id.name` field (so
`resource.resource.name` stays in sync for free) and **derive** it in `create`/`write`
rather than redefining it as a computed field; we **drop the inverse** (override the
reverse split to a no-op) so a prefixed name is never decomposed; and we **keep
full_name's create-time split** so the name-only creation paths that still exist
(res.users → employee, demo data, recruitment without name parts) continue to seed the
parts. The English `name_secondary` has no resource link and is already a computed
field, so there we simply override the compute to prepend the English title. Net effect:
the parts and `prefix_id`/`role` are the single source of truth; `name` is
display-/report-facing output that users never edit directly.

## Considered Options

- **Redefine `name` as a computed field (drop `related`)**: the most literal "compute",
  but it decouples `name` from `resource.resource.name`, leaving the backend Technical ▸
  Resource menus showing a stale name after a rename, and would need an explicit
  write-back to the resource to avoid that.
- **Keep the two-way inverse and strip the prefix before splitting**: fragile — it has
  to recognise every possible title string to peel it off, and a new title format
  silently corrupts the parts.
- **Only change the display (`name_get`)**: leaves the stored `name` title-less, so
  reports, exports and e-Saraban documents that read `name` directly never show the
  title — which was the whole point.
