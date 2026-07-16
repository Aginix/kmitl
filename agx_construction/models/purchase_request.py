from odoo import api, fields, models


class PurchaseRequest(models.Model):

    _inherit = "purchase.request"

    project_id = fields.Many2one(
        comodel_name="construction.project",
        string="Construction Project",
        domain=[("state", "=", "in_progress")],
        states={
            "reserve_budget": [("readonly", True)],
            "confirm": [("readonly", True)],
            "to_submit": [("readonly", True)],
            "to_approve": [("readonly", True)],
            "egp": [("readonly", True)],
            "approved": [("readonly", True)],
            "in_pa": [("readonly", True)],
            "purchasing": [("readonly", True)],
            "done": [("readonly", True)],
            "cancel": [("readonly", True)],
        },
    )

    def action_open_in_new_tab(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web#model=purchase.request&id={self.id}&view_type=form",
            "target": "new",
        }

    @api.onchange("is_construction")
    def _onchange_is_construction(self):
        if self.is_construction:
            self.payment_type = "direct"
