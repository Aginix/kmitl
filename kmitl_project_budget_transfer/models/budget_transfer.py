from odoo import api, fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    kmitl_project_line_ids = fields.Many2many(
        "budget.move.line",
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_line_ids",
        help="FROM/TO lines that carry a project dimension.",
    )
    # Mark the transfers a Direct Floating Allocation (ADR-0009) or a Floating
    # Return (ADR-0011) creates — they post on confirm, without the e-Saraban
    # approval, so they stay auditable.
    is_floating_allocation = fields.Boolean(
        string="จัดสรรตรงจากงบลอย",
        readonly=True,
        copy=False,
        help="โอนจากเงินลอยเข้ามิติโครงการโดยตรงจากหน้าโครงการ "
        "(ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)",
    )
    is_floating_return = fields.Boolean(
        string="โอนคืนงบลอย",
        readonly=True,
        copy=False,
        help="โอนเงินจากมิติโครงการคืนแหล่งที่มาโดยตรงจากหน้าโครงการ "
        "(ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)",
    )
    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        readonly=True,
        copy=False,
        index=True,
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

    def _skip_submit_review(self):
        return (
            self.is_floating_allocation
            or self.is_floating_return
            or super()._skip_submit_review()
        )
