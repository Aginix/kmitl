from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    READONLY_STATES = {
        "to_verify": [("readonly", True)],
        "to_send": [("readonly", True)],
        "sent": [("readonly", True)],
        "approved": [("readonly", True)],
        "actual": [("readonly", True)],
        "billed": [("readonly", True)],
        "rejected": [("readonly", True)],
        "returned": [("readonly", True)],
    }

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        states=READONLY_STATES,
        default=lambda self: self.env["res.users"].operating_unit_default_get(
            self.env.uid
        ),
    )
