# IAM delegation model: implied erp_manager + a single escalation guard

The IAM app exposes user / role / group / operating-unit / access-right /
record-rule administration through one group, `iam.group_iam_manager`, which
**implies `base.group_erp_manager`**. Core already grants `erp_manager` full
CRUD on those models, so every screen works on **default permissions** — the
app adds no ACLs or record rules of its own (except the single `operating.unit`
row the OU extension needs). Access Rights (`ir.model.access`) and Record Rules
(`ir.rule`) are left **fully editable** at that default level; we deliberately
did **not** build read-only `write()`-overrides for them.

The one deviation from default is a Python constraint,
`res.users._check_iam_no_system_escalation`, which forbids any
non-`group_system` user from causing a user to hold `base.group_system`
(directly, via an implied group/role, or via `res.groups.users`). This is what
makes **"IAM Manager ≠ full Settings admin"** actually true; without it the app
would merely relocate the Settings menus without reducing anyone's power.

## Considered options

- **A Python constraint, not an `ir.rule`** — chosen because `Many2many.write_real`
  runs `Command.LINK` as a raw `INSERT … ON CONFLICT DO NOTHING` with no
  `check_access_rule` on the comodel, so a record rule on `res.groups` cannot
  block `user.write({'groups_id': [(4, system_id)]})`. The constraint checks the
  resulting state and is the only enforcement point that actually holds.
- **Global scope, not OU/faculty-scoped** — an IAM Manager manages *all* users.
  Per-unit delegated admins (a faculty admin sees only their faculty's users)
  were considered and deferred; that needs record rules on `res.users` and is a
  larger surface for a later phase.
- **Default-editable ACLs/rules, not hardened read-only** — keeping the app a
  thin re-home of existing actions was preferred over pulling forward the
  `write()`-override hardening.

## Consequences

- The IAM Manager is a **trusted delegated administrator**, one tier below full
  Settings — not hardened against a hostile insider. They retain write on
  `ir.model.access` / `ir.rule` and could in principle author a permissive
  rule to escalate indirectly. Hardening (write-overrides on those two models,
  and on `ir.actions.server` / `ir.cron`) is a known future option,
  intentionally not built now.
- An IAM Manager **cannot edit the group membership of an existing full admin**
  (a user holding `group_system`): the constraint fires on any `groups_id`
  write to such a user. Intended — delegated admins don't touch Settings admins.
- `erp_manager` also carries some access beyond the stated scope (e.g. company
  records). Accepted under the same trusted-delegated posture.
