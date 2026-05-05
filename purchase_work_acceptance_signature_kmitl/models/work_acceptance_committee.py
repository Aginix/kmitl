import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WorkAcceptanceCommittee(models.Model):
    _inherit = "work.acceptance.committee"

    signature_image = fields.Image(
        string="Committee Signature",
        attachment=True,
        copy=False,
        readonly=True,
        help="Signature of the committee member captured when the row is marked accepted.",
    )

    def write(self, vals):
        result = super().write(vals)
        if vals.get("status") == "accept":
            for rec in self:
                if not rec.signature_image:
                    user = rec.employee_id.user_id
                    if not user:
                        _logger.warning(
                            "Employee %s has no linked user, "
                            "signature not captured for committee record %s",
                            rec.employee_id.display_name,
                            rec.id,
                        )
                    elif user.signature_image:
                        super(WorkAcceptanceCommittee, rec).write(
                            {"signature_image": user.signature_image}
                        )
                    else:
                        _logger.warning(
                            "User %s has no signature_image set, "
                            "signature not captured for committee record %s",
                            user.name,
                            rec.id,
                        )
        return result

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("signature_image")
        return res
