from odoo import _, models
from odoo.exceptions import UserError


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    def _has_pending_plan_transfer(self):
        """Held Money: a transfer into or out of the plan's dimension that has
        not posted, been cancelled or rejected yet."""
        if super()._has_pending_plan_transfer():
            return True
        if not self.analytic_account_id:
            return False
        return bool(
            self.env["budget.transfer"]
            .sudo()
            .search_count(
                [
                    # Not just draft/submitted: verify/e-Saraban bridges add
                    # to_verify, sent and returned on the way to posting.
                    ("state", "not in", ("posted", "cancelled", "rejected")),
                    (
                        "line_ids.procurement_plan_analytic_id",
                        "=",
                        self.analytic_account_id.id,
                    ),
                ]
            )
        )

    def _check_floating_return_allowed(self):
        """Any Budget User may return a plan's money, in any state, once the plan
        has its own dimension (ADR-0005/0006)."""
        self.ensure_one()
        if not (
            self.env.user.has_group("budget.group_budget_user") or self.env.is_admin()
        ):
            raise UserError(
                _("เฉพาะเจ้าหน้าที่งบประมาณ (Budget User) เท่านั้นที่โอนคืนงบลอยของแผนได้")
            )
        if not self.analytic_account_id or not self.budget_account_id:
            raise UserError(_("แผนนี้ยังไม่มีมิติแผนหรือรหัสงบประมาณ จึงไม่มีเงินให้โอนคืน"))

    def action_open_floating_return(self):
        """Open the โอนคืนงบลอย wizard."""
        self._check_floating_return_allowed()
        return {
            "type": "ir.actions.act_window",
            "name": _("โอนคืนงบลอย"),
            "res_model": "procurement.plan.floating.return",
            "view_mode": "form",
            "target": "new",
            "context": {"default_plan_id": self.id},
        }
