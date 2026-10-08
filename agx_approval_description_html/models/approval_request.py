from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    description = fields.Html(
        tracking=True,
        sanitize=True,
    )
