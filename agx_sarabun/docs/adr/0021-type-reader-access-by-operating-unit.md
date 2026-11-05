# ADR-0021 — Type reader access by Operating Unit

**Status:** Accepted
**Date:** 2026-11-04
**Modules:** `agx_sarabun_operating_unit`, `agx_sarabun_document_type_access`,
`agx_sarabun_operating_unit_access_all`

**Amends [ADR-0013](./0013-e-saraban-access-control-model.md)** (who may read a
หนังสือ). Every ADR-0013 rule stays as it is.

---

Two roles must read หนังสือ they are not routed to: สำนักงานคลังส่วนกลาง reads every
หนังสือขออนุมัติเบิกเงิน, and a unit's เจ้าหน้าที่พัสดุ reads every พ.1 / พจ.1 of its own
OU. So a หนังสือ gets an **OU**, a document type gets **reader groups**, and one group
lifts the OU scope.

- **OU of the หนังสือ** (`agx_sarabun_operating_unit`): one `operating_unit_id`,
  taken at creation from the origin record's `operating_unit_id` when it has one
  (`_sarabun_origin_operating_unit`, overridable), else the creator's default OU.
  It is a snapshot: it does not follow later edits of the origin. Existing หนังสือ are
  backfilled by `post_init_hook` with the same logic (origin table, then the sender's
  default OU). The module changes no access.
- **Type reader** (`agx_sarabun_document_type_access`): a member of
  `sarabun.document.type.reader_group_ids` reads every **non-draft** หนังสือ of that
  type whose OU is one of theirs. Read-only on the หนังสือ and on its Route (step,
  recipient, step↔activity rules alongside), exactly like a follower; never enters
  `reached_user_ids`, so no Incoming entry and no activity.
  They browse these under a menu **หนังสือของหน่วยงาน** (non-draft หนังสือ of
  their reader types), hidden from users who read no type.
- **Access all OUs** (`agx_sarabun_operating_unit_access_all`):
  `group_all_ou_sarabun_document` adds the same rules **without** the OU term. The user
  must still be a type reader.

Drafts stay private to their sender (`state != 'draft'`); returned, completed,
rejected and cancelled หนังสือ remain readable. Admins pick the reader groups on the
type form and grant them through roles; no seed module.

## Considered options

- **Global OU rule, like the other `*_operating_unit` modules** (rejected): a global
  rule is ANDed with the group rules, so it can only narrow access — it would hide
  other OUs' หนังสือ from Managers and routed actors and grant nobody anything new.
  The type-reader rules are **additive group rules** (ORed with ADR-0013's).
- **Rewrite the OU rule's `domain_force` from the access-all module**, as
  `agx_approval_operating_unit_access_all` does (rejected): a separate rule on the
  access-all group is simpler and leaves the OU-scoped rule untouched on uninstall.
- **Derive the OU from the sender's department** (rejected): would need
  `hr_department_operating_unit`; the origin already carries the authoritative OU.
- **Live (related) OU from the origin** (rejected): origins without the field would
  have none, and a later OU edit would silently move read access.

## Deploy

1. `-i agx_sarabun_operating_unit,agx_sarabun_document_type_access,agx_sarabun_operating_unit_access_all`
   (new modules: `-u` never installs them).
2. On ประเภทหนังสือ set "Reader Groups (by OU)" for หนังสือขออนุมัติเบิกเงิน, พ.1 and พจ.1.
3. Add `Access all OUs' หนังสือสารบรรณ` to the สำนักงานคลังส่วนกลาง role (users are
   role-managed; a group written on a user directly is wiped).
