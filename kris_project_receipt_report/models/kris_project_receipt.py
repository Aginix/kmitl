from odoo import fields, models


class KrisProjectReceipt(models.Model):
    _inherit = "kris.project.receipt"

    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        related="project_id.account_fiscal_year_id",
        store=True,
        index=True,
    )
    project_type_id = fields.Many2one(
        comodel_name="kris.project.type",
        string="ประเภทโครงการ",
        related="project_id.project_type_id",
        store=True,
        index=True,
    )
