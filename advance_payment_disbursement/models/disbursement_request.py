from odoo import api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
        compute="_compute_advance_payment_id",
        store=True,
    )

    @api.depends("purchase_request_approval_id.request_id.advance_payment_id")
    def _compute_advance_payment_id(self):
        for rec in self:
            approval = rec.purchase_request_approval_id
            if approval and approval.request_id:
                rec.advance_payment_id = approval.request_id.advance_payment_id
            else:
                rec.advance_payment_id = False
