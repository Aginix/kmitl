from odoo import _, models
from odoo.exceptions import UserError


class BudgetCommitmentSplit(models.Model):
    _inherit = "budget.commitment.split"

    def _check_editable(self):
        """ผู้จองงบประมาณ พ.1 holds full access to split rows for its พ.1's
        slip only — never a standalone draft slip's (budget ADR-0020)."""
        super()._check_editable()
        if (
            self.env.su
            or self.env.context.get("budget_split_sync")
            or self.env.user.has_group("budget.group_budget_user")
        ):
            return
        for commitment in self.commitment_id:
            if not commitment.sudo().purchase_request_ids:
                raise UserError(
                    _("ใบจอง %s แก้ไขรายการจองงบประมาณ (ถัวจ่าย) ในขั้นนี้ไม่ได้")
                    % commitment.display_name
                )
