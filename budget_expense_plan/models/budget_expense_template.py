# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetExpenseTemplate(models.Model):
    """Template (แม่แบบแผนเบิกจ่าย) -- the central, shared definition, one per
    (แหล่งเงิน x ปีงบประมาณ). It OWNS the whole structure (ADR-0004, ADR-0005):

    * **Budget Lines** (``line_ids``): the รายการงบ catalog for this template
      (label + category + ``expr``).
    * **Fund -> Budget Lines** (``fund_ids``): which รายการงบ appear under each
      กองทุน.
    * **Activity -> Funds** (``activity_ids``): which กองทุน apply under each
      ด้าน/แผนงาน/กิจกรรม.

    Because everything lives under the template, duplicating it copies the whole
    structure (with internal links remapped) so a new fiscal year is just
    "duplicate + change the year". A ส่วนงาน does not inherit a fixed set of
    activities: it *chooses* its own activities on the Plan Document.
    """

    _name = "budget.expense.template"
    _description = "Expense Plan Template (แม่แบบแผนเบิกจ่าย)"
    _order = "fiscal_year_id desc, source_analytic_id, id"

    name = fields.Char(string="ชื่อแม่แบบ", required=True, translate=True)
    fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year", string="ปีงบประมาณ"
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
        comodel_name="budget.expense.line",
        inverse_name="template_id",
        string="รายการงบ",
    )
    fund_ids = fields.One2many(
        comodel_name="budget.expense.template.fund",
        inverse_name="template_id",
        string="กองทุน & รายการงบ",
    )
    activity_ids = fields.One2many(
        comodel_name="budget.expense.template.activity",
        inverse_name="template_id",
        string="ด้าน/แผนงาน & กองทุน",
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
            if not template.fiscal_year_id:
                raise UserError(_("กรุณาระบุปีงบประมาณก่อนเผยแพร่"))
            if not template.line_ids:
                raise UserError(_("ต้องตั้งค่ารายการงบอย่างน้อย 1 รายการก่อนเผยแพร่"))
            if not template.fund_ids:
                raise UserError(_("ต้องตั้งค่ากองทุนอย่างน้อย 1 รายการก่อนเผยแพร่"))
            if not template.activity_ids:
                raise UserError(_("ต้องตั้งค่าด้าน/แผนงานอย่างน้อย 1 รายการก่อนเผยแพร่"))
            template.state = "published"

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def copy(self, default=None):
        """Deep-copy the template for a new fiscal year, remapping the internal
        Fund->Budget-Line and Activity->Fund links to the new copies (ADR-0005).
        The year is cleared so the user picks the next year before publishing;
        plans are never copied."""
        self.ensure_one()
        default = dict(default or {})
        default.setdefault("state", "draft")
        default.setdefault("fiscal_year_id", False)
        default.setdefault("name", _("%s (สำเนา)") % (self.name or ""))
        # handle children manually so M2m links can be remapped
        default.update({"line_ids": [], "fund_ids": [], "activity_ids": [], "plan_ids": []})
        new = super().copy(default)

        line_map = {}
        for line in self.line_ids:
            line_map[line.id] = line.copy({"template_id": new.id}).id
        fund_map = {}
        for fund in self.fund_ids:
            new_fund = fund.copy(
                {
                    "template_id": new.id,
                    "budget_line_ids": [
                        (6, 0, [line_map[l.id] for l in fund.budget_line_ids if l.id in line_map])
                    ],
                }
            )
            fund_map[fund.id] = new_fund.id
        for act in self.activity_ids:
            act.copy(
                {
                    "template_id": new.id,
                    "fund_ids": [
                        (6, 0, [fund_map[f.id] for f in act.fund_ids if f.id in fund_map])
                    ],
                }
            )
        return new

    def action_duplicate(self):
        """Duplicate this template (for the next year) and open the copy."""
        self.ensure_one()
        new = self.copy()
        return {
            "type": "ir.actions.act_window",
            "name": _("แม่แบบแผนเบิกจ่าย"),
            "res_model": "budget.expense.template",
            "res_id": new.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_generate_plans(self):
        """Push-generate one draft Plan Document per Required Department that
        does not yet have one for this Template (ADR-0002). Each ส่วนงาน then
        chooses its own activities."""
        self.ensure_one()
        Plan = self.env["budget.expense.plan"]
        required = self.env["budget.expense.required.department"].search(
            [("company_id", "=", self.company_id.id)]
        )
        if not required:
            raise UserError(_("ยังไม่ได้ตั้งค่า 'ส่วนงานที่ต้องทำแผน' — กรุณาตั้งค่าก่อน"))
        existing_dept_ids = Plan.search([("template_id", "=", self.id)]).mapped(
            "department_analytic_id"
        ).ids
        for req in required:
            if req.department_analytic_id.id in existing_dept_ids:
                continue
            Plan.create(
                {
                    "template_id": self.id,
                    "department_analytic_id": req.department_analytic_id.id,
                }
            )
        return self.action_view_plans()

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


class BudgetExpenseTemplateFund(models.Model):
    """Fund composition: which รายการงบ (Budget Lines) appear under a กองทุน."""

    _name = "budget.expense.template.fund"
    _description = "Expense Plan Template Fund"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="budget.expense.template",
        string="แม่แบบ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    fund_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="กองทุน",
        required=True,
        domain="[('root_plan_id.code', '=', 'funds')]",
    )
    budget_line_ids = fields.Many2many(
        comodel_name="budget.expense.line",
        string="รายการงบ",
        domain="[('template_id', '=', parent.id)]",
    )
    display_name = fields.Char(compute="_compute_display_name")
    company_id = fields.Many2one(related="template_id.company_id", store=True)

    _sql_constraints = [
        (
            "unique_fund",
            "unique(template_id, fund_analytic_id)",
            "กองทุนนี้ถูกตั้งค่าในแม่แบบแล้ว",
        ),
    ]

    @api.depends("fund_analytic_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.fund_analytic_id.display_name


class BudgetExpenseTemplateActivity(models.Model):
    """Activity composition: which กองทุน apply under a ด้าน/แผนงาน/กิจกรรม."""

    _name = "budget.expense.template.activity"
    _description = "Expense Plan Template Activity"
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
    fund_ids = fields.Many2many(
        comodel_name="budget.expense.template.fund",
        relation="budget_exp_tmpl_activity_fund_rel",
        string="กองทุน",
        domain="[('template_id', '=', parent.id)]",
    )
    display_name = fields.Char(compute="_compute_display_name")
    company_id = fields.Many2one(related="template_id.company_id", store=True)

    _sql_constraints = [
        (
            "unique_activity",
            "unique(template_id, activity_analytic_id)",
            "ด้าน/แผนงานนี้ถูกตั้งค่าในแม่แบบแล้ว",
        ),
    ]

    @api.depends("activity_analytic_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.activity_analytic_id.display_name
