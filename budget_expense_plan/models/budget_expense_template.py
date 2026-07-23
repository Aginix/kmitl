# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetExpenseTemplate(models.Model):
    """Template (แม่แบบแผนเบิกจ่าย) -- the central, shared grid.

    One per (แหล่งเงิน x ปีงบประมาณ): the set of Activities in scope and, under
    each, the (Fund, Budget Line) pairs that must be planned. Every ส่วนงาน's
    Plan Document renders this grid live (ADR-0002); a Template edit therefore
    propagates immediately.
    """

    _name = "budget.expense.template"
    _description = "Expense Plan Template (แม่แบบแผนเบิกจ่าย)"
    _order = "fiscal_year_id desc, source_analytic_id, id"

    name = fields.Char(string="ชื่อแม่แบบ", required=True, translate=True)
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
    )
    source_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="แหล่งเงิน",
        required=True,
        domain="[('root_plan_id.code', '=', 'sources')]",
    )
    state = fields.Selection(
        selection=[("draft", "ร่าง"), ("published", "เผยแพร่")],
        string="สถานะ",
        default="draft",
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="budget.expense.template.line",
        inverse_name="template_id",
        string="แถวแม่แบบ",
    )
    plan_ids = fields.One2many(
        comodel_name="budget.expense.plan",
        inverse_name="template_id",
        string="เอกสารแผน",
    )
    plan_count = fields.Integer(compute="_compute_plan_count")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "unique_fy_source_company",
            "unique(fiscal_year_id, source_analytic_id, company_id)",
            "มีแม่แบบสำหรับปีงบประมาณและแหล่งเงินนี้อยู่แล้ว",
        ),
    ]

    @api.depends("plan_ids")
    def _compute_plan_count(self):
        data = self.env["budget.expense.plan"].read_group(
            [("template_id", "in", self.ids)], ["template_id"], ["template_id"]
        )
        mapped = {d["template_id"][0]: d["template_id_count"] for d in data}
        for template in self:
            template.plan_count = mapped.get(template.id, 0)

    def action_publish(self):
        for template in self:
            if not template.line_ids.filtered("active"):
                raise UserError(_("ต้องมีแถวแม่แบบอย่างน้อย 1 แถวก่อนเผยแพร่"))
            template.state = "published"

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_generate_plans(self):
        """Push-generate one draft Plan Document per Required Department that
        does not yet have one for this Template (ADR-0002)."""
        self.ensure_one()
        Plan = self.env["budget.expense.plan"]
        required = self.env["budget.expense.required.department"].search(
            [("company_id", "=", self.company_id.id)]
        )
        if not required:
            raise UserError(
                _("ยังไม่ได้ตั้งค่า 'ส่วนงานที่ต้องทำแผน' — กรุณาตั้งค่าก่อน")
            )
        existing = Plan.search([("template_id", "=", self.id)])
        existing_dept_ids = existing.mapped("department_analytic_id").ids
        created = Plan
        for req in required:
            if req.department_analytic_id.id in existing_dept_ids:
                continue
            created |= Plan.create(
                {
                    "template_id": self.id,
                    "department_analytic_id": req.department_analytic_id.id,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารแผนเบิกจ่าย"),
            "res_model": "budget.expense.plan",
            "view_mode": "tree,form",
            "domain": [("template_id", "=", self.id)],
            "context": {"default_template_id": self.id},
        }

    def action_view_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารแผนเบิกจ่าย"),
            "res_model": "budget.expense.plan",
            "view_mode": "tree,form",
            "domain": [("template_id", "=", self.id)],
            "context": {"default_template_id": self.id},
        }


class BudgetExpenseTemplateLine(models.Model):
    """A Template row = (Activity, Fund, Budget Line). Plan amounts key to this
    row's id (stable id, ADR-0002), so editing the row re-labels existing
    amounts and archiving it (``active=False``) soft-hides them for audit."""

    _name = "budget.expense.template.line"
    _description = "Expense Plan Template Line"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="budget.expense.template",
        string="แม่แบบ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    activity_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        required=True,
        domain="[('root_plan_id.code', '=', 'activities')]",
    )
    fund_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="กองทุน",
        required=True,
        domain="[('root_plan_id.code', '=', 'funds')]",
    )
    budget_line_id = fields.Many2one(
        comodel_name="budget.expense.line",
        string="รายการงบ",
        required=True,
        ondelete="restrict",
    )
    category_id = fields.Many2one(
        related="budget_line_id.category_id", store=True, string="หมวดงบรายจ่าย"
    )
    display_name = fields.Char(compute="_compute_display_name")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related="template_id.company_id", store=True)

    _sql_constraints = [
        (
            "unique_row",
            "unique(template_id, activity_analytic_id, fund_analytic_id, budget_line_id)",
            "แถวนี้ (กิจกรรม/กองทุน/รายการงบ) มีอยู่แล้วในแม่แบบ",
        ),
    ]

    @api.depends("activity_analytic_id", "fund_analytic_id", "budget_line_id")
    def _compute_display_name(self):
        for line in self:
            parts = [
                line.activity_analytic_id.display_name,
                line.fund_analytic_id.display_name,
                line.budget_line_id.name,
            ]
            line.display_name = " / ".join(p for p in parts if p)
