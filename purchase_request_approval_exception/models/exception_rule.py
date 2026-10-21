from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    purchase_request_approval_ids = fields.Many2many(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approvals",
    )
    model = fields.Selection(
        selection_add=[("purchase.request.approval", "Purchase Request Approval")],
        ondelete={"purchase.request.approval": "cascade"},
    )
    method = fields.Selection(
        selection_add=[
            (
                "purchase_request_approval_check_partner_required",
                "Purchase Request Approval: Vendor set before ส่งเข้าสารบรรณ",
            ),
        ],
    )
