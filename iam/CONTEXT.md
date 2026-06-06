# Context — iam (Identity & Access Management)

A standalone backend **app** for delegated user/security administration, so that
managing users no longer requires full Settings (`base.group_system`) or Admin.

## Glossary

- **IAM Manager** (`iam.group_iam_manager`) — the one group this module adds. A
  *delegated administrator* with **global** scope (manages every backend user,
  not a single faculty/OU — per-OU delegation is a later phase). Manages backend
  users, roles, groups, access rights and record rules. Implies
  `base.group_erp_manager` (the source of all its ORM rights). Does **not** imply
  `base.group_system`.
- **Backend (internal) user** — `share = False`. The only users in scope; portal
  and public users are out of scope.

## Why this works without Settings

`base.group_erp_manager` already has full CRUD on `res.users`, `res.groups`,
`ir.rule`, `ir.model.access` (core `base/security/ir.model.access.csv`) and, via
`base_user_role`, on `res.users.role`(`.line`). Core only buried the *menus* for
groups/rules/access under Settings ▸ Technical. This app just re-homes those
existing actions under its own menu — **no new actions, no new models** except a
single `res.users` constraint. Group hierarchy: `group_system` ⊃
`group_erp_manager` ⊃ `group_user`.

## The privilege boundary (and what is NOT closed)

- **Closed:** minting new full admins. `res.users._check_iam_no_system_escalation`
  blocks any non-system user from making any user hold `base.group_system`
  (direct, implied-through-a-group/role, or via `res.groups.users`). Implied
  groups materialise into `groups_id` at write time, so checking the *resulting
  state* covers the indirect paths too.
- **Why a Python constraint, not an `ir.rule`:** `Many2many.write_real`
  (`odoo/fields.py`) runs `Command.LINK` as a raw `INSERT ... ON CONFLICT DO
  NOTHING` with no `check_access_rule` on the target — so a record rule on
  `res.groups` does **not** stop `user.write({'groups_id': [(4, system_id)]})`.
  The constraint catches the effect; the rule would have been theatre.
- **Residual (decided, not a gap):** Access Rights / Record Rules are left
  **editable at the default `erp_manager` level** — the app deliberately adds no
  read-only override. So the Manager can still author/relax `ir.model.access` /
  `ir.rule` rows to escalate indirectly: a *trusted* delegated admin, one tier
  below Settings. Hardening (`write()` overrides on those two models) is a known
  future option, intentionally not built now. See `docs/adr/0001`.

## Companion modules

- `iam_operating_unit` — adds the *Operating Units* menu + the one extra ACL row
  OU needs (core grants `operating.unit` write only to
  `operating_unit.group_manager_operating_unit`, never to `erp_manager`), and
  appends `operating_unit.group_multi_operating_unit` to the IAM Manager so the
  OU menu and the user-form OU widget are visible. It deliberately does **not**
  imply `group_manager_operating_unit`, which would silently grant data access to
  every OU across all business modules.
