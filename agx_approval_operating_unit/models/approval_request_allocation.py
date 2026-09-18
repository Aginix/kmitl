from odoo import fields, models


class ApprovalRequestAllocation(models.Model):
    _inherit = "approval.request.allocation"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="request_id.operating_unit_id",
        string="Operating Unit",
    )
