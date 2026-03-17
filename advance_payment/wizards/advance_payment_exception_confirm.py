from odoo import fields, models


class AdvancePaymentExceptionConfirm(models.TransientModel):
    _name = "advance.payment.exception.confirm"
    _description = "Advance Payment Exception Confirm"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Advance Payment",
    )

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.button_draft()
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        return super().action_confirm()
