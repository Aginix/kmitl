from odoo import api, fields, models


class PurchaseRequest(models.Model):

    _inherit = "purchase.request"

    is_construction = fields.Boolean(string="Construction", readonly=True)

    project_id = fields.Many2one(
        comodel_name="construction.project",
        string="Construction Project",
        domain=[("state", "=", "in_progress")],
    )

    @api.onchange("is_construction")
    def _onchange_is_construction(self):
        if self.is_construction:
            self.payment_type = "direct"
