# Auto-inject the assignment buttons above the sheet via `assignment.mixin`

The Assign to me / Assign… / Unassign buttons used to be added to the
`<header>` of each consuming form by per-model view XML
(`//header/button[1] position="before"`), where they sat mixed in with the
document's own workflow buttons (Submit, Approve, …). They are now rendered
inside a dedicated alert box injected **above the sheet** at view-build time:
the plain-Python `AssignedOfficerMixin` was lifted into an Odoo
`AbstractModel` (`assignment.mixin`) whose `get_view()` renders the QWeb
template `templates/assignment_templates.xml` and inserts it before
`/form/sheet` — the same mechanism `base_tier_validation` uses for its
`tier_validation_label`.

A consuming model opts in by inheriting the mixin and declaring its two group
hooks; it writes **no view XML** for the buttons:

```python
class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "assignment.mixin"]
    _assign_user_group = "purchase.group_purchase_user"
    _assign_manager_group = "purchase.group_purchase_manager"
    assigned_to = fields.Many2one("res.users", ...)
```

The group hooks are passed to the template as render params
(`t-attf-groups="#{user_group}"`), the way `base_tier_validation`
parameterises its templates with `state_field`/`state_value`.

## Why

- **Assignment actions are not workflow actions.** Mixed into the header they
  read as document state transitions; users could not tell "claim this work"
  apart from "approve this document". A separate alert box above the sheet
  gives them their own visual home on every consuming form, uniformly.
- **Consumers get the UI for free.** Adding assignment to a new document type
  previously meant repeating a three-button header block per form view (and
  keeping the invisible helper field in sync). With injection it is one
  `_inherit` plus two class attributes — the buttons, helper field and
  visibility rules travel with the mixin.
- **The lift was already planned.** The plain mixin's docstring reserved this
  exact move ("when a non-purchase document needs the same behaviour, lift
  this into an `assignment.mixin`"); the `__slots__` workaround it needed
  disappears with a real AbstractModel.

## Considered options

- **Keep header buttons, restyle them** (e.g. a separate `<div>` inside the
  header): still per-form XML for every consumer, and the header remains a mix
  of workflow and assignment actions. **Rejected.**
- **A `t-call`-able template consumers reference from their own view XML**:
  explicit, no `get_view` magic, but every consumer still writes view XML —
  which is the thing this change removes. **Rejected.**

## Consequences

- Every form view of a consuming model pays a small `get_view` cost (one QWeb
  render + arch parse), the same price `base_tier_validation` pays.
- The buttons no longer exist in any stored view arch; view customisations
  must target the template (or override `get_view`), not xpath the buttons.
- The assignment activity moved off the native To-Do type onto a dedicated
  `mail_activity_assignment` type, so the Todo-inbox bridge
  (`procurement_assignment_todo`) can tag just this type with a
  `todo_category` — and `_assignment_clear_activity` can no longer collide
  with a user-scheduled native To-Do (the summary-matching heuristic is gone).
