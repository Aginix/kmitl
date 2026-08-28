from odoo import fields, models


class PurchaseRequestExceptionConfirm(models.TransientModel):
    _inherit = ["purchase.request.exception.confirm"]

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.button_draft()
            self.related_model_id.ignore_exception = True
            self.related_model_id.button_to_verify()
