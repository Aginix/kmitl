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

## Why the mixin does not `_inherit = mail.thread`

The mixin uses `activity_schedule`, `activity_ids` and `message_post`, all
of which live on `mail.thread` / `mail.activity.mixin`. It would look
cleaner to declare `_inherit = "mail.thread"` here so the mixin advertises
that contract itself — and an earlier draft did exactly that.

That draft crashed at install with:

```
TypeError: Cannot create a consistent method resolution order (MRO) for bases
  BaseModel, base, mail.thread, mail.activity.mixin, portal.mixin,
  budget.commitment.mixin, base.exception, assignment.mixin
```

The consuming model was `disbursement.request`, which already inherits
`mail.thread`, `mail.activity.mixin`, `portal.mixin`,
`budget.commitment.mixin` and `base.exception`. When `assignment.mixin` is
appended with `mail.thread` in its own bases, Python's C3 linearization
sees `mail.thread` on two independent parents (once directly, once as an
ancestor of `mail.activity.mixin`) with no consistent ordering — and
refuses to build the class.

The mixin therefore inherits **only** from `BaseModel` (via
`models.AbstractModel`). All chatter/activity calls resolve at runtime on
the *consumer* record — every real consumer already inherits
`mail.activity.mixin` for its own reasons (any document worth assigning has
a chatter), so `self.activity_schedule(...)` still works. This constraint
is documented on the mixin's class docstring; do not add
`_inherit = "mail.thread"` back in.

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

## Extension points

The mixin exposes every knob a real-world consumer has needed so far, so
customization is a matter of overriding a hook — never rewriting the mixin.

**Class attributes** (set on the consuming model, read at view-render time):

| Attribute | Default | Purpose |
|---|---|---|
| `_assign_user_group` | `None` (required) | xmlid of the group that can self-claim |
| `_assign_manager_group` | `None` (required) | xmlid of the group that can reassign / unassign |
| `_assignment_manual_config` | `False` | Set `True` to skip the auto-injected alert — the Python API (`action_assignment_*`) is unaffected, so consumers can render their own banner or expose the actions from the header |
| `_assignment_alert_xpath` | `"/form/sheet"` | Where in the form arch the alert is inserted |
| `_assignment_alert_position` | `"before"` | `"before"` / `"after"` / `"inside"` relative to the xpath match |

**Method hooks** (override on the consuming model):

| Hook | Default returns | Called from |
|---|---|---|
| `_assignment_activity_xmlid()` | `"base_assignment.mail_activity_assignment"` | `_assignment_notify` / `_assignment_clear_activity` |
| `_assignment_activity_summary()` | `_("Assigned as responsible officer")` | `_assignment_notify` |
| `_assignment_takeover_param()` | `None` | `_assignment_takeover_allowed` |
| `_assignment_takeover_default()` | `False` | `_assignment_takeover_allowed` |
| `_assignment_on_assigned(new, old)` | `None` (no-op) | After every write that sets `assigned_to` (claim, wizard reassign) |
| `_assignment_on_unassigned(old)` | `None` (no-op) | After `assigned_to` is cleared |

The lifecycle hooks let a consumer react to any assignment change without
overriding the action methods themselves — useful when the reaction is
side-channel (send an email, transition a workflow state, post to chatter).
Both hooks fire on the record after the write, so `self.assigned_to`
reflects the new value.

The `_assignment_manual_config` toggle exists for two situations we already
know about: a document that renders its own dashboard-style card and does
not want a duplicate banner, and a document whose form is unusual enough
(no `<sheet>`, or a `<sheet>` inside another wrapper) that the default
xpath does not match. If just the location is wrong, retarget with
`_assignment_alert_xpath` / `_assignment_alert_position`; use manual config
only when the banner has to be gone entirely.

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
