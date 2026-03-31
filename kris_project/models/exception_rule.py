from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    kris_project_ids = fields.Many2many(
        comodel_name="kris.project",
        string="KRIS Projects",
    )
    model = fields.Selection(
        selection_add=[
            ("kris.project", "KRIS Project"),
        ],
        ondelete={"kris.project": "cascade"},
    )
