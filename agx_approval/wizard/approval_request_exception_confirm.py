from odoo import fields, models


class ApprovalRequestExceptionConfirm(models.TransientModel):
    _name = "approval.request.exception.confirm"
    _description = "Approval Request Exception Wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("approval.request", "Approval Request")

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.ignore_exception = True
        return super().action_confirm()
