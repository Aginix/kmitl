from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_pr_owner_or_manager = fields.Boolean(
        compute="_compute_is_pr_owner_or_manager",
    )

    @api.depends("requested_by")
    def _compute_is_pr_owner_or_manager(self):
        user = self.env.user
        is_privileged = user.has_group(
            "purchase_request.group_purchase_request_manager"
        ) or user.has_group(
            "purchase_request_kmitl.group_purchase_request_user_all"
        )
        for rec in self:
            rec.is_pr_owner_or_manager = (
                is_privileged or rec.requested_by.id == user.id
            )
