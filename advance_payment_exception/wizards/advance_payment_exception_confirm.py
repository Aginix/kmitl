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
        if self.ignore and not self.exception_ids.filtered("is_blocking"):
            # Ignoring non-blocking exceptions: re-run the submit so the
            # request advances properly (assigns the number, checks the
            # one-active rule, posts the message) — now that the exception is
            # ignored the popup is skipped.
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        else:
            self.related_model_id.ignore_exception = False
        return super().action_confirm()
