from odoo import fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    disbursement_request_ids = fields.One2many(
        'disbursement.request',
        'advance_payment_id',
        string='Disbursement Requests'
    )

    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request_count",
    )

    def _compute_disbursement_request_count(self):
        for rec in self:
            rec.disbursement_request_count = len(rec.disbursement_request_ids)
