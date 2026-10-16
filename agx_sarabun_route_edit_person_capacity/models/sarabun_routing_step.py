"""Correct the capacity a signed บุคลากร step was signed in (ADR-0019).

A route editor may re-label the ตำแหน่ง (capacity) of a positively signed Person-mode
step — while circulating AND after completion — when it was genuinely wrong. Only
the capacity changes: the signer's name, signature image and date stay as signed.
The rendered block reads the signing snapshot first (ADR-0009), so the snapshot is
rewritten together with the step's capacity. The new Position must be one the person
currently holds (the same rule ``agx_sarabun_person_capacity`` enforces at signing).
Deliberately not logged to the chatter — only route editors may do it.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.agx_sarabun.models.sarabun_routing_step import POSITIVE_DISPOSITIONS
from odoo.addons.agx_sarabun_route_edit.models.sarabun_document import (
    ROUTE_EDIT_GROUP,
)


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    can_edit_signed_capacity = fields.Boolean(
        compute="_compute_can_edit_signed_capacity",
        help="True when the current user may correct the ตำแหน่ง this signed บุคลากร "
        "step was signed in — drives the row button on the Route.",
    )

    def _is_signed_capacity_editable(self):
        self.ensure_one()
        return (
            self.state == "done"
            and self.disposition in POSITIVE_DISPOSITIONS
            and self.target_mode == "person"
            and self.verb.show_signature
            and not self.is_originator
            and self.document_id.state in ("circulating", "completed")
        )

    @api.depends(
        "state",
        "disposition",
        "target_mode",
        "verb.show_signature",
        "is_originator",
        "document_id.state",
    )
    def _compute_can_edit_signed_capacity(self):
        is_editor = self.env.user.has_group(ROUTE_EDIT_GROUP)
        for step in self:
            step.can_edit_signed_capacity = (
                is_editor and step._is_signed_capacity_editable()
            )

    def _check_signed_capacity_editable(self):
        self.ensure_one()
        if not self.env.user.has_group(ROUTE_EDIT_GROUP):
            raise UserError(
                _("Only a Sarabun Route Editor may correct a signed capacity.")
            )
        if not self._is_signed_capacity_editable():
            raise UserError(
                _(
                    "Only the ตำแหน่ง of a signed บุคลากร step on a circulating or "
                    "completed document can be corrected."
                )
            )

    def action_open_signed_capacity_wizard(self):
        self.ensure_one()
        self._check_signed_capacity_editable()
        return {
            "type": "ir.actions.act_window",
            "name": _("แก้ไขตำแหน่งที่ลงนาม"),
            "res_model": "sarabun.signed.capacity.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_step_id": self.id,
                "default_position_id": self.position_id.id,
            },
        }

    def _set_signed_capacity(self, position):
        """Re-label the capacity: the step's ``position_id`` (the capacity label),
        the authoritative ``signed_as_position_id`` when the verb recorded one, and
        the frozen ``signed_position_name`` the signature block prints."""
        self.ensure_one()
        self._check_signed_capacity_editable()
        if self.employee_id not in position.sudo()._current_holder_employees():
            raise UserError(
                _("%(person)s does not hold the position %(position)s.")
                % {
                    "person": self.employee_id.display_name,
                    "position": position.display_name,
                }
            )
        vals = {"position_id": position.id, "signed_position_name": position.name}
        if self.signed_as_position_id:
            vals["signed_as_position_id"] = position.id
        # sudo: a signed step is locked to every user write (and a completed หนังสือ
        # is read-only); the authority was checked above.
        self.sudo().write(vals)
