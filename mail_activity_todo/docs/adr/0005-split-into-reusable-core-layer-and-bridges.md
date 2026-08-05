# Split into a reusable core, a role-in-unit layer, and per-app bridges

The module originally shipped as one addon, `kmitl_todo`, that depended on
`base_user_role`, `operating_unit`, `procurement_plan_operating_unit`,
`purchase_request_approval` and `purchase_request_activity_kmitl`. That made the
generic Todo engine un-installable anywhere it wasn't accompanied by KMITL's
procurement stack, and tied a reusable idea to one institution's name. We split
it into four addons and renamed the engine so it can be reused elsewhere.

```
mail_activity_todo            core engine          depends: mail
  └─ mail_activity_todo_role_unit   group routing   depends: + base_user_role, operating_unit
       └─ procurement_plan_todo     UC1 bridge      depends: + procurement_plan_operating_unit
mail_activity_todo            ← purchase_request_todo  UC2/UC3 bridge (core only)
                                                    depends: + purchase_request_approval, purchase_request_activity_kmitl
```

## Why

- **The core must stand alone.** Personal (`user_id`) Todos, the inbox, the
  read state (`todo.read`), the completed history (`todo.log`), the systray and
  the retention cron need nothing beyond `mail`. `purchase_request_todo` depends
  on the core *only* — a working proof that the engine is independent of the
  role-in-unit machinery.
- **Group routing is one optional concern.** `responsible_role_id` +
  `operating_unit_id` and the live `role ∩ OU` resolution (ADR-0002) pull in
  `base_user_role` + `operating_unit`. Isolating them in
  `mail_activity_todo_role_unit` keeps those deps off the core.
- **Business integrations are bridges**, mirroring the pattern the ROADMAP
  already prescribes for the `tier.validation` bridge: a per-app addon that
  depends on the engine (and the layer if it needs group routing), never the
  other way around. The engine never depends on a business module.
- **De-KMITL the names** so the engine reads as a general capability: module
  `mail_activity_todo`; models `todo.read` / `todo.log`; config key
  `mail_activity_todo.fyi_retention_days`; bus channel
  `mail_activity_todo/updated`; `res.users.todo_role_ids`.

## How the core stays extensible

- `mail.activity._my_todo_domain()` returns the personal branch in the core;
  the layer overrides it to OR-in the `role ∩ OU` branch. `is_my_todo`, the
  systray count and the inbox action all key off this one hook, so they extend
  automatically.
- `mail.activity._todo_recipient_partners()` (bus fan-out) resolves the personal
  assignee in the core; the layer adds the live role-in-unit members.
- `todo.log._todo_log_vals(activity)` builds the snapshot dict in the core; the
  layer adds `responsible_role_id` / `operating_unit_id`.
- Completed-Todo visibility is two OR-combined `ir.rule` records: the core's
  personal rule plus the layer's role-in-unit rule on the same group.
- `user_id` is relaxed to non-required by the layer (group Todos have no single
  assignee); the core keeps native semantics.

## Considered options

- **Keep `base_user_role` + `operating_unit` in the core** (only break out the
  business modules): simpler, but leaves the engine tied to an org model it does
  not conceptually need, and a generic deployment without operating units could
  not use it. **Rejected** in favour of a clean `mail`-only core.

## Consequences

- Renaming the module/models is not an in-place Odoo operation: an existing
  `kmitl_todo` install must be uninstalled and the new addons installed (a fresh
  install on a pre-production database; no data migration written).
- ADR-0001..0004 describe the design as first built under the single-module
  name; the mechanism is unchanged, only its packaging and identifiers.
