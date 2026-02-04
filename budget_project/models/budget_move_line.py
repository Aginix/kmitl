from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    is_project = fields.Boolean(
        related="account_id.is_project",
        store=True,
        readonly=True,
    )

    project_id = fields.Many2one(comodel_name="kmitl.project", string="โครงการ/กิจกรรม")
    # project_analytic_id = fields.Many2one("account.analytic.account")
