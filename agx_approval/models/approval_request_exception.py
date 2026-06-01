from odoo import api, models


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = ["approval.request", "base.exception"]
    _order = "main_exception_id asc, name desc"

    @api.model
    def _reverse_field(self):
        return "approval_request_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "agx_approval.action_approval_request_exception_confirm"
        )

    def _popup_exceptions(self):
        action = super()._popup_exceptions()
        action["context"]["agx_exception_action"] = self.env.context.get(
            "agx_exception_action", False
        )
        return action
