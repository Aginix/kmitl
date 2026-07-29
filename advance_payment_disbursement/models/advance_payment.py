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

    def _action_do_cancel(self, reason):
        self.ensure_one()
        if self.reference_model == "purchase.request":
            self.reference.button_rejected()
        return super()._action_do_cancel(reason)
