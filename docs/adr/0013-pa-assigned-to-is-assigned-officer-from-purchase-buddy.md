# พจ.1 `assigned_to` is the Assigned Officer (เจ้าหน้าที่ผู้รับผิดชอบ), defaulted from the Purchase Buddy settings

## Status

Accepted. Supersedes [ADR-0001](0001-assigned-officer-model.md) for
`purchase.request.approval`.

## Context

กองพัสดุ wants to set up which เจ้าหน้าที่พัสดุ looks after which ส่วนงาน, and wants
every พจ.1 to show that person as its **เจ้าหน้าที่ผู้รับผิดชอบ**. Budget already does
the same thing for budget documents with `budget_buddy`.

ADR-0001 kept the PA's `assigned_to` as "Approver", but nothing ever filled it:
`_prepare_approval_vals` writes `False`, and the form shows it read-only. Since
[ADR-0011](0011-pr-assigned-to-is-designated-verifier.md) took the PR's `assigned_to`,
the **Assigned Officer** has had no home.

## Decision

- **The PA's `assigned_to` now means the Assigned Officer.** It is relabelled
  เจ้าหน้าที่ผู้รับผิดชอบ by a new bridge, `purchase_request_approval_buddy`
  (auto-install). The base module is not edited.
- **A new `purchase_buddy` module holds the coverage settings.** It is a copy of
  `budget_buddy` with its own model (`purchase.buddy`), group (เจ้าหน้าที่ Buddy (พัสดุ),
  category-less, implies Purchase Request User) and menu (Purchase > Configuration).
  A row is a generic `model_id + domain`, so a PR or PO could be covered later with no
  schema change.
- **The default comes only from the Buddy settings.** `assigned_to` is a stored compute
  with `readonly=False`:
  - it takes the first matching Buddy by sequence, typically matched on
    `requesting_department_id child_of …`;
  - it depends on `requesting_department_id` and `department_analytic_id`;
  - while the PA is `draft`, `sarabun_returned` or `pending_pr`, a pick the settings
    no longer cover is replaced and a covered pick is kept; after that the value is
    frozen.
- **The bridge drops `assigned_to` from `_prepare_approval_vals`.** An explicit `False`
  would stop the compute. On a ตีกลับ/แก้ไข resync this also keeps the officer.
- **The field is optional.** Anyone in the Buddy group may be picked, while
  `is_editable` allows. God Mode leaves it locked.
- **Scope**: the field, an "ที่ฉันรับผิดชอบ" filter, a list column and a group-by.
  There is no Todo and no record-rule change; access stays with the OU rules.

## Considered options

- **A new field instead of reusing `assigned_to`**: rejected. It would leave a dead
  field next to it, the same reasoning ADR-0011 used on the PR.
- **Share `budget.buddy`**: rejected. Purchase would come to depend on budget, and
  procurement and budget officers are different people with different lists.
- **Extract a generic buddy base out of `budget_buddy`**: rejected for now.
  `budget_buddy` is live, so moving its model needs an xmlid pre-migration. The cost
  is a duplicated `_resolve_hierarchy`, which must be fixed in both copies if it
  changes.
- **Key the default on the budget Department or the OU**: rejected. Procurement serves
  the unit that asks, and the Requesting Department is the PA's own copied field.

## Consequences

- PAs that exist before installation keep `False`. Nothing re-computes them unless one
  of the dependent fields changes while the PA is still open.
- A central Buddy outside the PA's OU may be named yet unable to open the PA. Access
  still comes from Allowed OUs / access-all.
- On an existing database, deploy with `-i purchase_buddy,purchase_request_approval_buddy`.
  `-u` does not install a new auto-install module.
