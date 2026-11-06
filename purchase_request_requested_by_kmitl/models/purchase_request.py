from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    can_edit_requested_by = fields.Boolean(
        compute="_compute_can_edit_requested_by",
    )

    @api.depends_context("uid")
    def _compute_can_edit_requested_by(self):
        can_edit = self.env.user.has_group(
            "purchase_request_kmitl.group_purchase_request_user_all"
        )
        for rec in self:
            rec.can_edit_requested_by = can_edit
