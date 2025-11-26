from odoo import _, api, fields, models


class AccountExpenseRequestDemo(models.Model):
    _name = "account.expense.request.demo"
    _inherit = ['account.expense.request', 'tier.validation']
    _description = "Account Expense Request Demo"

    _state_from = ["submitted"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
        tracking=True,
        required=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        required=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
        tracking=True,
        required=True,
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        tracking=True,
        required=True,
        states=READONLY_STATES,
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="รหัสค่าใช้จ่าย",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        tracking=True,
        required=True,
        states=READONLY_STATES,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence number"""
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "account.expense.request.demo"
                ) or "/"
        return super().create(vals_list)

    def action_submit(self):
        """Override submit to auto-trigger tier validation."""
        # Call parent to move to submitted state
        res = super().action_submit()

        # Auto-trigger tier validation if needed
        for record in self:
            if record.need_validation and record.state == "submitted":
                record.request_validation()

        return res

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.action_approve()
