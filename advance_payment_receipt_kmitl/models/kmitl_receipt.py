from odoo import fields, models


class KmitlReceipt(models.Model):
    _inherit = "kmitl.receipt"

    advance_return_line_id = fields.Many2one(
        comodel_name="advance.payment.return.line",
        string="Advance Return Line",
        readonly=True,
        copy=False,
    )
    advance_agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Advance Payment Agreement",
        related="advance_return_line_id.agreement_id",
        store=True,
    )

    def action_view_advance_agreement(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "advance.payment",
            "res_id": self.advance_agreement_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }
