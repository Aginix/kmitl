# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BudgetExpensePlan(models.Model):
    """Plan Document (เอกสารแผนเบิกจ่าย) -- a ส่วนงาน's holder of monthly แผน
    figures for one (แหล่งเงิน, ปีงบ). Carries state/ownership/access; its grid
    is rendered live from the Template (not snapshotted, ADR-0002). Actual (ผล)
    is derived from budget consume (ADR-0003), never stored here.

    State: draft -> confirmed (ส่วนงาน submits) -> active (central approves and
    locks; แผน no longer editable).
    """

    _name = "budget.expense.plan"
    _description = "Expense Plan Document (เอกสารแผนเบิกจ่าย)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fiscal_year_id desc, department_analytic_id, id"
    _check_company_auto = True

    name = fields.Char(
        string="เลขที่",
        required=True,
        copy=False,
        readonly=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    template_id = fields.Many2one(
        comodel_name="budget.expense.template",
        string="แม่แบบ",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    fiscal_year_id = fields.Many2one(
        related="template_id.fiscal_year_id", store=True, string="ปีงบประมาณ"
    )
    source_analytic_id = fields.Many2one(
        related="template_id.source_analytic_id", store=True, string="แหล่งเงิน"
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="ส่วนงาน",
        required=True,
        domain="[('root_plan_id.code', '=', 'departments')]",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("confirmed", "ยืนยันแผน"),
            ("active", "แผนใช้งาน"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    amount_ids = fields.One2many(
        comodel_name="budget.expense.plan.amount",
        inverse_name="plan_id",
        string="ยอดแผนรายเดือน",
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total", string="ยอดแผนรวม"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Currency"
    )

    _sql_constraints = [
        (
            "unique_template_department",
            "unique(template_id, department_analytic_id)",
            "มีเอกสารแผนของส่วนงานนี้สำหรับแม่แบบนี้อยู่แล้ว",
        ),
    ]

    @api.depends("amount_ids.amount")
    def _compute_amount_total(self):
        for plan in self:
            plan.amount_total = sum(plan.amount_ids.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("budget.expense.plan")
                    or _("New")
                )
        return super().create(vals_list)

    def name_get(self):
        result = []
        for plan in self:
            bits = [plan.name]
            if plan.department_analytic_id:
                bits.append(plan.department_analytic_id.display_name)
            if plan.fiscal_year_id:
                bits.append(plan.fiscal_year_id.name)
            result.append((plan.id, " · ".join(b for b in bits if b)))
        return result

    def action_confirm(self):
        self.filtered(lambda p: p.state == "draft").write({"state": "confirmed"})

    def action_activate(self):
        self.filtered(lambda p: p.state == "confirmed").write({"state": "active"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_open_grid(self):
        """Open the OWL entry/compare grid for this Plan Document."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "budget_expense_plan_grid",
            "name": self.display_name,
            "params": {"plan_id": self.id},
            "context": {"active_id": self.id},
        }


class BudgetExpensePlanAmount(models.Model):
    """A sparse monthly plan cell: (Plan Document, Template row, month) -> แผน
    amount. Only filled cells exist. Locked once the Plan Document is active."""

    _name = "budget.expense.plan.amount"
    _description = "Expense Plan Monthly Amount"
    _order = "template_line_id, month"

    plan_id = fields.Many2one(
        comodel_name="budget.expense.plan",
        string="เอกสารแผน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    template_line_id = fields.Many2one(
        comodel_name="budget.expense.template.line",
        string="แถวแม่แบบ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    month = fields.Integer(string="เดือน", required=True)
    amount = fields.Monetary(string="ยอดแผน", currency_field="currency_id")
    currency_id = fields.Many2one(related="plan_id.currency_id")
    company_id = fields.Many2one(related="plan_id.company_id", store=True)

    _sql_constraints = [
        (
            "unique_cell",
            "unique(plan_id, template_line_id, month)",
            "มียอดแผนของแถว/เดือนนี้อยู่แล้ว",
        ),
        (
            "month_range",
            "CHECK(month >= 1 AND month <= 12)",
            "เดือนต้องอยู่ระหว่าง 1 ถึง 12",
        ),
    ]

    @api.constrains("plan_id")
    def _check_plan_not_locked(self):
        for rec in self:
            if rec.plan_id.state == "active":
                raise ValidationError(
                    _("แผนอยู่ในสถานะ 'แผนใช้งาน' (ล็อก) แก้ไขยอดไม่ได้")
                )

    def write(self, vals):
        self._assert_unlocked()
        return super().write(vals)

    def unlink(self):
        self._assert_unlocked()
        return super().unlink()

    def _assert_unlocked(self):
        if any(rec.plan_id.state == "active" for rec in self):
            raise UserError(
                _("แผนอยู่ในสถานะ 'แผนใช้งาน' (ล็อก) แก้ไขยอดไม่ได้")
            )
