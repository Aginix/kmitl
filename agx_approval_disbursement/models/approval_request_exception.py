from odoo import models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def action_create_disbursement_request(self):
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                agx_exception_action="action_create_disbursement_request"
            )._popup_exceptions()
        return super().action_create_disbursement_request()
