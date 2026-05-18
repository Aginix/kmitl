from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    approval_request_ids = fields.Many2many(
        comodel_name="approval.request",
        string="Approval Requests",
    )
    model = fields.Selection(
        selection_add=[("approval.request", "Approval Request")],
        ondelete={"approval.request": "cascade"},
    )
