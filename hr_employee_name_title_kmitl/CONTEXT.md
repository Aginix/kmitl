# HR Employee Name Title KMITL

Composes the employee's name as "title prefix + name parts" and locks it: the stored
`hr.employee.name` is derived from the person's name parts plus a work-track-dependent
title prefix, and is never edited directly or split back into parts.

## Language

**Employee Name (ชื่อพนักงาน)**: The stored, locked `name` —
`{Title Prefix}{firstname} {middlename} {lastname}` (Thai; the prefix is glued to the
first name with no space). Derived in `create`/`write` from the name parts and the Title
Prefix; writing it directly has no lasting effect (it is re-derived), and it is never
inverse-split into parts. _Avoid_: full name, display name

**Title Prefix (คำนำหน้าตามสายงาน)**: The string placed before the name, chosen by the
employee's work track (`role`). Academic-track staff use their
[[hr-employee-academic-standing-thailand]] Academic Standing Title; support-track and
untracked staff use their personal honorific (`prefix_id`, นาย/นาง/นางสาว). An
academic-track employee with no academic title falls back to the honorific. _Avoid_:
salutation, honorific (that word names only the `prefix_id` half)

**Name Parts (ชื่อแยกส่วน)**: The [[kmitl-hr-employee-full-name]] `firstname` /
`middlename` / `lastname` (and their `_secondary` English counterparts) — the editable
source of truth for a person's name, as opposed to the derived Employee Name.
