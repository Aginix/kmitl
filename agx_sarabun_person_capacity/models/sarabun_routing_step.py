"""Person-mode capacity label — keep the step's three target fields in a clean
state when the user flips mode or re-picks the person.

The core engine already reads ``self.position_id`` as the signing capacity
(``_resolve_capacity`` / ``_signature_snapshot_vals``), so no engine changes are
needed; this add-on only teaches the view surface to surface + clean the value.
"""

from odoo import _, api, models
from odoo.exceptions import UserError


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    @api.onchange("target_mode")
    def _onchange_target_mode_reset_targets(self):
        """Wipe every target field when the mode flips — a leftover employee from a
        prior person-mode edit, or a stale position from a prior position-mode edit,
        would otherwise ride along silently into the new mode (shown by the stored
        FK but hidden under the new mode's attrs) and get snapshotted at send."""
        if self.is_originator:
            return
        self.position_id = False
        self.employee_id = False
        self.department_id = False

    @api.onchange("employee_id")
    def _onchange_employee_clear_capacity(self):
        """In person mode the capacity dropdown is filtered to the pinned person's
        current holdings; a value from the previous person may no longer be valid."""
        if self.target_mode != "person" or self.is_originator:
            return
        self.position_id = False

    def _resolve_capacity(self, signed_as_position_id):
        """Person mode: the capacity is only a label picked client-side (template
        lines aren't filtered, holdings change) — refuse to sign under a title the
        pinned person doesn't hold rather than print it on the official document."""
        capacity = super()._resolve_capacity(signed_as_position_id)
        if (
            self.target_mode == "person"
            and capacity
            and self.employee_id not in capacity._current_holder_employees()
        ):
            raise UserError(
                _(
                    "%(person)s does not hold the position %(position)s — "
                    "update the step's signing capacity (ลงนามในฐานะ)."
                )
                % {
                    "person": self.employee_id.display_name,
                    "position": capacity.display_name,
                }
            )
        return capacity
