from odoo import api, fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    kmitl_project_line_ids = fields.Many2many(
        "budget.move.line",
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_line_ids",
        help="FROM/TO lines that carry a project dimension.",
    )

    @api.depends(
        "from_line_ids.kmitl_project_analytic_id",
        "to_line_ids.kmitl_project_analytic_id",
    )
    def _compute_kmitl_project_line_ids(self):
        for transfer in self:
            transfer.kmitl_project_line_ids = (
                transfer.from_line_ids | transfer.to_line_ids
            ).filtered("kmitl_project_analytic_id")
