from odoo import api, fields, models


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
        capture_ids = []
        if vals.get("status") == "accept":
            capture_ids = [
                rec.id
                for rec in self
                if rec.status != "accept" and not rec.signature_image
            ]
        result = super().write(vals)
        if capture_ids:
            for rec in self.browse(capture_ids):
                user = rec.employee_id.user_id
                if user and user.signature_image:
                    super(WorkAcceptanceCommittee, rec).write(
                        {"signature_image": user.signature_image}
                    )
        return result

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("signature_image")
        return res
