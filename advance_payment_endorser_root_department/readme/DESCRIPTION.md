Suggests the ผู้บังคับบัญชา (`endorser_id`) of a loan from the borrower's top-level unit
(คณะ/สำนัก — the `hr.department` with no parent) instead of their line manager
(`parent_id`):

- the top-level unit's `manager_id`;
- the borrower's line manager when the borrower is that manager;
- nobody when the unit has no manager, so submit is blocked until someone is picked.

The value stays overridable, as in advance_payment ADR-0020.
