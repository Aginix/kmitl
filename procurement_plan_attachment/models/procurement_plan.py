from odoo import fields, models


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "procurement.plan")],
    )
