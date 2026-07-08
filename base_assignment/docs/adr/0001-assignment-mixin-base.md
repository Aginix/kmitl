# `base_assignment` — a reusable Assigned Officer mixin

`base_assignment` gives any business document ("purchase.request",
"disbursement.request", or a future one) an *Assigned Officer* concept —
"who is currently responsible for this record" — plus a uniform UI
(Assign to me / Assign… / Unassign) rendered as an alert box injected above
the form's sheet, following the `base_tier_validation` pattern.

Consumers opt in by inheriting `assignment.mixin`, declaring their two group
hooks, and providing the `assigned_to` field. No view XML is written for the
buttons; no wizard is written for the manager reassignment flow.

## Why a dedicated base module

Two independent consumers had grown parallel implementations of the same
behaviour: `procurement_assignment_kmitl` (three-button header on
purchase.request / purchase.order) and `disbursement/*_assignment.py`
(identical methods, identical wizard shape, different config parameter,
plus routing rules on top). Keeping both in step meant editing two
near-identical files; adding a third consumer (advance payment, work
acceptance, …) meant a third copy.

Lifting the mixin into a `mail`-only module removes that duplication and
gives any future consumer a one-line opt-in.

## API

Consumers configure per-model behaviour through two class attributes and
four method hooks. The class attributes are required; the method hooks all
have sensible defaults and are overridden only when the consumer needs
different behaviour:

```python
class MyDoc(models.Model):
    _name = "my.doc"
    _inherit = ["my.doc", "assignment.mixin"]
    _assign_user_group = "my_module.group_my_officer"
    _assign_manager_group = "my_module.group_my_manager"
    assigned_to = fields.Many2one("res.users", ...)

    # Optional overrides:
    def _assignment_activity_xmlid(self):
        return "base_assignment.mail_activity_assignment"
    def _assignment_activity_summary(self):
        return _("Assigned as responsible officer")
    def _assignment_takeover_param(self):
        return None  # or "my_module.allow_takeover_assigned"
    def _assignment_takeover_default(self):
        return False
```

The class attributes are hooks (not fields) so `get_view` — running before
any record is loaded — can read them synchronously to render the template.

## Config parameter contract

The takeover toggle uses an ir.config_parameter owned by the *consumer*
(e.g. `procurement_assignment_kmitl.allow_takeover_assigned`,
`disbursement.allow_takeover_assigned`) — not by `base_assignment`. Each
consumer can therefore pick its own default (procurement defaults to False,
disbursement defaults to True), keep the Settings UI toggle in its own
module, and remove the toggle entirely by leaving
`_assignment_takeover_param()` returning `None`. This matches how the rest
of this repo scopes `ir.config_parameter` keys.

## Activity type

`base_assignment.mail_activity_assignment` is a dedicated
`mail.activity.type` (not the native `mail.mail_activity_data_todo`) so the
optional Todo-inbox bridge can tag *just this type* with a `todo_category`
and `_assignment_clear_activity` can match on the type alone (no fragile
summary-substring heuristics that would collide with user-scheduled
To-Dos).

## Considered options

- **Keep the mixin in `procurement_assignment_kmitl` and depend on it from
  `disbursement`**: works, but every non-procurement consumer would pull in
  a procurement-shaped dependency graph they do not need, and the module
  name misleads. **Rejected.**
- **Ship the mixin as a plain Python class (no `AbstractModel`)**: what the
  earlier draft in procurement did (`__slots__` workaround). Reusable in
  code, but a plain class cannot own `get_view`, so every consumer would
  have to write the header XML. **Rejected** in favour of the AbstractModel
  approach that `base_tier_validation` uses.
- **Share `ir.config_parameter` across consumers**: one takeover key that
  every consumer honours. Simpler storage, but forces one default across
  domains that legitimately want different ones (procurement's conservative
  "manager reassigns" vs disbursement's advisory "any officer can grab
  mis-routed work"). **Rejected.**
