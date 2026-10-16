from odoo import _, models
from odoo.exceptions import UserError

# From ส่งเข้าแผน (the analytic exists) until the project closes (ADR-0009).
FLOATING_ALLOCATION_STATES = ("to_verify", "to_send", "sent", "returned", "in_progress")


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _check_floating_allocation_allowed(self):
        self.ensure_one()
        if not (
            self.env.user.has_group("budget.group_budget_user") or self.env.is_admin()
        ):
            raise UserError(
                _("เฉพาะเจ้าหน้าที่งบประมาณ (Budget User) เท่านั้นที่จัดสรรงบประมาณได้")
            )
        if self.state not in FLOATING_ALLOCATION_STATES or not self.analytic_account_id:
            raise UserError(
                _("จัดสรรงบประมาณ (งบลอย) ได้ตั้งแต่ส่งเข้าแผนจนถึงระหว่างดำเนินโครงการ")
            )
        if not self.budget_account_id:
            raise UserError(_("กรุณาระบุรหัสงบประมาณของโครงการก่อน"))

    def action_open_floating_allocation(self):
        """Open the จัดสรรงบประมาณ (งบลอย) wizard (ADR-0009)."""
        self._check_floating_allocation_allowed()
        return {
            "type": "ir.actions.act_window",
            "name": _("จัดสรรงบประมาณ (งบลอย)"),
            "res_model": "kmitl.project.floating.allocation",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }
