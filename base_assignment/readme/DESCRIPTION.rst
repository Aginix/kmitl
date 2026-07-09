Business documents often need to track a single **Assigned Officer**
(เจ้าหน้าที่ผู้รับผิดชอบ) — the person currently accountable for moving the
record forward. Without a shared foundation, every module that needs this
ends up copying the same three buttons (Assign to me / Assign… / Unassign),
the same reassignment wizard, and the same follow-up To-Do.

This module ships that foundation as a single ``AbstractModel``
(``assignment.mixin``) plus a QWeb template that Odoo auto-injects above
the ``<sheet>`` of any consuming form — mirroring the pattern used by
``base_tier_validation``. A consumer opts in with one ``_inherit`` line,
two group hooks, and the ``assigned_to`` field.

**Note:** This module provides no user-facing feature on its own. It is a
foundation for other modules to inherit from.

See ``procurement_assignment_kmitl`` (purchase.request, purchase.order) and
``disbursement`` (disbursement.request) in this repository as reference
implementations.
