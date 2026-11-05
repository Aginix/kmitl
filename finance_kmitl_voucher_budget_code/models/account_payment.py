from odoo import _, fields, models
from odoo.exceptions import UserError

# Plan code → label of the dimensions an opted-in voucher must carry. The
# project and procurement-plan dimensions stay optional: not every source has them.
REQUIRED_DIMENSIONS = [
    ("departments", "ส่วนงาน"),
    ("sources", "แหล่งเงิน"),
    ("funds", "กองทุน"),
    ("activities", "ด้าน/แผนงาน/กิจกรรม"),
]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        copy=False,
        index=True,
    )
    is_budget_code_required = fields.Boolean(
        compute="_compute_is_budget_code_required",
        help="Technical: the voucher needs its รหัสงบประมาณ and core dimensions"
        " before ยืนยันส่งธนาคาร. Source modules opt in by overriding the compute.",
    )

    def _compute_is_budget_code_required(self):
        self.is_budget_code_required = False

    def action_confirm_for_bank(self):
        self._check_voucher_budget_complete()
        return super().action_confirm_for_bank()

    def _check_voucher_budget_complete(self):
        for payment in self.filtered("is_budget_code_required"):
            dimensions = payment._voucher_dimensions()
            missing = [
                label for code, label in REQUIRED_DIMENSIONS if code not in dimensions
            ]
            if not payment.budget_account_id:
                missing.append("รหัสงบประมาณ")
            if missing:
                raise UserError(
                    _("%(payment)s is missing: %(missing)s")
                    % {
                        "payment": payment.display_name,
                        "missing": ", ".join(missing),
                    }
                )
