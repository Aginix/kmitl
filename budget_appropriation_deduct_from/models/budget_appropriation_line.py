from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    deduct_from_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="หักจากรหัสงบประมาณ",
        domain="[('budget_type', '=', budget_type),"
        " ('deduct', '=', False), ('budgetable', '=', True)]",
        tracking=True,
        help="รหัสงบประมาณรายรับต้นทางที่ถูกหักโดยรายการหักโอนนี้",
    )

    @api.constrains("deduct", "deduct_from_account_id")
    def _check_deduct_from_account_id(self):
        for line in self:
            if line.deduct and not line.deduct_from_account_id:
                raise ValidationError(
                    _(
                        "กรุณาระบุรหัสงบประมาณต้นทางที่ต้องการหัก"
                        " สำหรับรายการหักโอน: %s"
                    )
                    % (line.account_id.display_name or "")
                )
