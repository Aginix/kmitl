from odoo import fields, models


class PurchaseRequestApprovalExceptionConfirm(models.TransientModel):
    _name = "purchase.request.approval.exception.confirm"
    _description = "Purchase Request Approval exception wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one(
        "purchase.request.approval", "Purchase Request Approval"
    )

    def action_confirm(self):
        self.ensure_one()
        exceptions_blocking = self.exception_ids.filtered("is_blocking")
        if self.ignore and not exceptions_blocking:
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit_to_sarabun()
        else:
            self.related_model_id.ignore_exception = False
        return super().action_confirm()
