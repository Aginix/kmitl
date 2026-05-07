from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    @api.depends(
        "loan_amount",
        "usage_line_ids.amount",
        "return_line_ids.amount",
        "return_line_ids.state",
    )
    def _compute_amounts(self):
        for rec in self:
            used = sum(rec.usage_line_ids.mapped("amount"))
            returned = sum(
                rec.return_line_ids.filtered(
                    lambda l: l.state == "done"
                ).mapped("amount")
            )
            rec.amount_used = used
            rec.amount_returned = returned
            rec.amount_remaining = rec.loan_amount - used - returned

    def _action_do_cancel(self, reason):
        self.ensure_one()
        if self.reference and self.reference._name == "purchase.request":
            self.reference.button_rejected()
        return super()._action_do_cancel(reason)

    def action_disburse(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(
                    _("Only approved agreements can be disbursed.")
                )
        self.write({
            "state": "in_progress",
            "disbursement_state": "paid",
        })
        for rec in self:
            rec.message_post(
                body=_("ดำเนินการเบิกจ่ายแล้ว"),
                subtype_xmlid="mail.mt_note",
            )
