from odoo import _, fields, models
from odoo.exceptions import ValidationError


class BudgetSelectionWizard(models.TransientModel):
    _name = "budget.selection.wizard"
    _inherit = ["base.exception"]
    _description = "Budget Selection Wizard"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    budget_account_id = fields.Many2one(
        "budget.account",
        string="รหัสงบประมาณ",
        domain=[("purchase_ok", "=", True), ("product_id", "!=", False)],
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
    )

    def action_apply(self):
        self.ensure_one()
        self._check_exception()
        record = self.env[self.res_model].browse(self.res_id)
        if not record.exists():
            raise ValidationError(_("Record not found."))

        # Build analytic_distribution from selected dimensions
        distribution = {}
        for analytic_field in [
            "activity_analytic_id",
            "department_analytic_id",
            "fund_analytic_id",
            "source_analytic_id",
        ]:
            analytic = getattr(self, analytic_field)
            if analytic:
                distribution[str(analytic.id)] = 100.0

        vals = {
            "analytic_distribution": distribution if distribution else False,
        }
        if "budget_account_id" in self.env[self.res_model]._fields:
            vals["budget_account_id"] = self.budget_account_id.id or False

        record.write(vals)
        return {"type": "ir.actions.act_window_close"}
