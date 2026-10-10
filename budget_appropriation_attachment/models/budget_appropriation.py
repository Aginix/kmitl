from odoo import fields, models


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "budget.appropriation")],
    )
