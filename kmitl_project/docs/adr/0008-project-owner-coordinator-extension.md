# Project Owners (incl. ผู้ประสานงาน) ship as an install-only extension that widens the base OU rule

The ผู้ประสานงาน (`coordinator_ids`, one or more per project) and the rights of a **Project Owner** —
หัวหน้าโครงการ, ผู้ประสานงาน or the creator — live in two new modules,
`kmitl_project_coordinator` and its auto-install glue
`kmitl_project_coordinator_sarabun`. They are not in `kmitl_project` /
`kmitl_project_sarabun`, because both are live in production and this way the feature is
a plain **install**: no existing module is upgraded or bumped.

## Why

- **Own Project for the coordinator is additive.** Odoo ORs group rules together, so a
  coordinator rule per model (project + its 5 child models) sits beside the base Own
  rules without editing them.
- **Cross-OU visibility can't be added the same way.** The base OU read rule is
  _global_, and global rules are ANDed, so no group rule can widen it. The extension
  therefore **rewrites the base record**
  (`kmitl_project.kmitl_project_operating_unit_rule`) to let owners in from any OU. This
  survives a later `-u kmitl_project`, because Odoo also upgrades installed dependents
  after the base. An `uninstall_hook` restores the original domain, since the widened
  one references `coordinator_ids`.
- **The ขออนุมัติ button gate needs both the coordinator and e-Saraban**, so it sits in
  an auto-install glue module. The coordinator module itself stays free of e-Saraban.

## Consequences

- The สร้างหนังสือ gate (owners + Officer/Manager) only applies when the coordinator
  module is installed. The base bridge alone still gates on state only.
- Status changes post under the new subtype `mt_kmitl_project_state` (default), so a
  newly created project's creator, as auto-follower, is also notified of status changes.
  Existing followers keep the subtypes they already have.
- Every owner must be a KMITL Project user, since the Own rules apply only to that group:
  the coordinator picker allows only such users, and the หัวหน้าโครงการ picker is
  narrowed to employees whose user is one (or who have no user).
- Folding this back into `kmitl_project` later means moving the field and an xmlid (see
  the field-move pre-migration pattern) and dropping the OU-rule override and its hook.
