from odoo import fields, models


class BudgetTransfer(models.Model):
    """Mark the transfers a Direct Floating Allocation creates (ADR-0009) — they
    post on confirm, without the e-Saraban approval, so they stay auditable."""

    _inherit = "budget.transfer"

    is_floating_allocation = fields.Boolean(
        string="จัดสรรตรงจากงบลอย",
        readonly=True,
        copy=False,
        help="โอนจากเงินลอยเข้ามิติโครงการโดยตรงจากหน้าโครงการ "
        "(ไม่ผ่านกระบวนการขออนุมัติโอนงบประมาณ)",
    )
    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        readonly=True,
        copy=False,
        index=True,
    )

    def _skip_submit_review(self):
        return self.is_floating_allocation or super()._skip_submit_review()
