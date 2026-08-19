from odoo import fields, models


class BudgetTransferExceptionConfirm(models.TransientModel):
    _name = "budget.transfer.exception.confirm"
    _description = "Budget Transfer exception wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("budget.transfer", "Budget Transfer")

    def action_confirm(self):
        self.ensure_one()
        exceptions_blocking = self.exception_ids.filtered("is_blocking")
        if self.ignore and not exceptions_blocking:
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        else:
            self.related_model_id.ignore_exception = False
        return super().action_confirm()
