from odoo import fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "budget.transfer")],
    )
