from odoo import api, fields, models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    responsible_signature = fields.Image(
        string="Receiver Signature",
        attachment=True,
        copy=False,
        readonly=True,
        help="Signature of the procurement officer (responsible_id) captured at acceptance.",
    )

    def button_accept(self, force=False):
        result = super().button_accept(force=force)
        for rec in self:
            if rec.state == "accept" and not rec.responsible_signature:
                signature = rec.responsible_id.signature_image
                if signature:
                    rec.with_context(skip_validation_check=True).write(
                        {"responsible_signature": signature}
                    )
        return result

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("responsible_signature")
        return res
