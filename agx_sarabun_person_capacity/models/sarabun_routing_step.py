"""Person-mode capacity label — keep the step's three target fields in a clean
state when the user flips mode or re-picks the person.

The core engine already reads ``self.position_id`` as the signing capacity
(``_resolve_capacity`` / ``_signature_snapshot_vals``), so no engine changes are
needed; this add-on surfaces + cleans the value, and guards (at send and at
signing) that the pinned person actually holds it.
"""

from odoo import _, api, models
from odoo.exceptions import UserError


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    def write(self, vals):
        """Extend the base originator write guard to also allow ``position_id``
        — the capacity the ผู้จัดทำ signs in. The base guard only permits
        ``verb``; we pop ``position_id`` before it runs, then write it back
        via sudo so the guard never sees it."""
        if (
            not self.env.su
            and "position_id" in vals
            and self.filtered("is_originator")
        ):
            pos_val = vals.pop("position_id")
            res = super().write(vals)
            self.sudo().write({"position_id": pos_val})
            return res
        return super().write(vals)

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

    def _check_person_capacity(self):
        """A person-mode capacity is only a label filtered client-side — template
        lines are unfiltered and holdings change — so refuse a capacity the pinned
        person doesn't hold rather than print it on the official document."""
        for step in self:
            if (
                step.target_mode == "person"
                and step.position_id
                and step.employee_id
                not in step.position_id.sudo()._current_holder_employees()
            ):
                raise UserError(
                    _(
                        "Step %(order)s: %(person)s does not hold the position "
                        "%(position)s — fix the signing capacity (ตำแหน่ง) on the "
                        "route (ตีกลับ first if the document is already circulating)."
                    )
                    % {
                        "order": step.order,
                        "person": step.employee_id.display_name,
                        "position": step.position_id.display_name,
                    }
                )

    def _signature_snapshot_vals(self, actor, capacity=False):
        # Covers every verb that prints a title (show_signature), not only the
        # is_signature ones _resolve_capacity validates.
        self._check_person_capacity()
        return super()._signature_snapshot_vals(actor, capacity)
