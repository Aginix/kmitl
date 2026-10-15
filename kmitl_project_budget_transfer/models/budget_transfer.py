from odoo import _, api, fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    kmitl_project_table = fields.Html(
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_table",
        sanitize=False,
    )

    @api.depends(
        "from_line_ids.kmitl_project_analytic_id",
        "from_line_ids.amount",
        "to_line_ids.kmitl_project_analytic_id",
        "to_line_ids.amount",
    )
    def _compute_kmitl_project_table(self):
        for transfer in self:
            transfer.kmitl_project_table = transfer._render_linked_record_table(
                "kmitl.project",
                "kmitl_project_analytic_id",
                _("ไม่มีโครงการ/กิจกรรมในใบโอนนี้"),
            )
