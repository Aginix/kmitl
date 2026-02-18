from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetAppropriationOnboarding(models.Model):
    _name = "budget.appropriation.onboarding"
    _description = "Budget Appropriation Onboarding"
    _order = "department_analytic_id"

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        readonly=True,
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments"), ("parent_id", "=", False)],
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    # Step 1: ทำประมาณการรายรับ-รายจ่าย
    step1_done = fields.Boolean(string="ขั้นตอนที่ 1 เสร็จสิ้น")
    step1_revenue_count = fields.Integer(
        string="รายรับ", compute="_compute_step1"
    )
    step1_expense_count = fields.Integer(
        string="รายจ่าย", compute="_compute_step1"
    )
    step1_submitted_count = fields.Integer(
        string="ส่งแล้ว", compute="_compute_step1"
    )
    step1_draft_count = fields.Integer(
        string="ร่าง", compute="_compute_step1"
    )
    step1_total_count = fields.Integer(
        string="ทั้งหมด", compute="_compute_step1"
    )

    # Step 2: ทำรวมเล่มหน่วยงาน
    step2_done = fields.Boolean(string="ขั้นตอนที่ 2 เสร็จสิ้น")
    step2_source_status_html = fields.Html(
        string="สถานะรวมเล่มตามแหล่งเงิน",
        compute="_compute_step2",
        sanitize=False,
    )
    step2_compilation_count = fields.Integer(
        string="จำนวนรวมเล่ม", compute="_compute_step2"
    )
    step2_pending_appropriation_count = fields.Integer(
        string="ประมาณการที่ยังไม่ได้รวมเล่ม", compute="_compute_step2"
    )

    # Step 3: ยืนยันส่งข้อมูลประมาณการ
    step3_done = fields.Boolean(string="ขั้นตอนที่ 3 เสร็จสิ้น")
    step3_submitted_count = fields.Integer(
        string="ยืนยันแล้ว", compute="_compute_step3"
    )
    step3_total_compilation_count = fields.Integer(
        string="รวมเล่มทั้งหมด", compute="_compute_step3"
    )

    # Overall
    progress = fields.Integer(
        string="ความคืบหน้า (%)", compute="_compute_progress"
    )

    _sql_constraints = [
        (
            "unique_fiscal_year_department",
            "UNIQUE(account_fiscal_year_id, department_analytic_id)",
            "มีข้อมูล Onboarding ของหน่วยงานนี้ในปีงบประมาณนี้แล้ว",
        ),
    ]

    def name_get(self):
        return [
            (
                rec.id,
                "{} - {}".format(
                    rec.department_analytic_id.name or "",
                    rec.account_fiscal_year_id.name or "",
                ),
            )
            for rec in self
        ]

    def _get_appropriations(self):
        self.ensure_one()
        return self.env["budget.appropriation"].search(
            [
                ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
                ("department_analytic_id", "=", self.department_analytic_id.id),
                ("state", "!=", "cancel"),
            ]
        )

    def _get_compilations(self):
        self.ensure_one()
        return self.env["budget.appropriation.compilation"].search(
            [
                ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
                ("department_analytic_id", "=", self.department_analytic_id.id),
            ]
        )

    def _compute_step1(self):
        for rec in self:
            appropriations = rec._get_appropriations()
            rec.step1_revenue_count = len(
                appropriations.filtered(lambda a: a.budget_type == "revenue")
            )
            rec.step1_expense_count = len(
                appropriations.filtered(lambda a: a.budget_type == "expense")
            )
            rec.step1_submitted_count = len(
                appropriations.filtered(lambda a: a.state in ("review", "posted"))
            )
            rec.step1_draft_count = len(
                appropriations.filtered(lambda a: a.state == "draft")
            )
            rec.step1_total_count = len(appropriations)

    def _compute_step2(self):
        all_sources = self.env["account.analytic.account"].search(
            [("root_plan_id.code", "=", "sources")],
            order="line_seq, code",
        )
        for rec in self:
            compilations = rec._get_compilations()
            rec.step2_compilation_count = len(compilations)

            # Find appropriations not linked to any compilation
            appropriations = rec._get_appropriations()
            linked_ids = set()
            for comp in compilations:
                linked_ids |= set(comp.revenue_appropriation_ids.ids)
                linked_ids |= set(comp.expense_appropriation_ids.ids)
            rec.step2_pending_appropriation_count = len(
                appropriations.filtered(lambda a: a.id not in linked_ids)
            )

            # Build source status HTML
            rows = []
            for source in all_sources:
                has = source.id in compilations.mapped("source_analytic_id").ids
                if has:
                    icon = (
                        '<i class="fa fa-check-circle text-success me-1"></i>'
                    )
                else:
                    icon = '<i class="fa fa-circle-o text-muted me-1"></i>'
                rows.append(
                    "<tr><td>{}{}</td></tr>".format(icon, source.name)
                )
            rec.step2_source_status_html = (
                '<table class="table table-sm table-borderless mb-0">'
                "{}</table>".format("".join(rows))
            )

    def _compute_step3(self):
        for rec in self:
            compilations = rec._get_compilations()
            rec.step3_total_compilation_count = len(compilations)
            rec.step3_submitted_count = len(
                compilations.filtered(
                    lambda c: c.state in ("confirmed", "done")
                )
            )

    def _compute_progress(self):
        for rec in self:
            steps_done = sum([rec.step1_done, rec.step2_done, rec.step3_done])
            rec.progress = int((steps_done / 3) * 100)

    @api.model
    def action_open_onboarding(self):
        """Auto-create onboarding records for current FY and open view."""
        today = fields.Date.context_today(self)
        fiscal_year = self.env["account.fiscal.year"].search(
            [
                ("date_from", "<=", today),
                ("date_to", ">=", today),
            ],
            limit=1,
        )
        if not fiscal_year:
            raise UserError(_("ไม่พบปีงบประมาณสำหรับวันที่ปัจจุบัน"))

        departments_plan = self.env["account.analytic.plan"].search(
            [("code", "=", "departments")], limit=1
        )
        root_departments = self.env["account.analytic.account"].search(
            [
                ("plan_id", "=", departments_plan.id),
                ("parent_id", "=", False),
            ]
        )

        existing_dept_ids = set(
            self.search(
                [("account_fiscal_year_id", "=", fiscal_year.id)]
            ).mapped("department_analytic_id.id")
        )

        vals_list = [
            {
                "account_fiscal_year_id": fiscal_year.id,
                "department_analytic_id": dept.id,
            }
            for dept in root_departments
            if dept.id not in existing_dept_ids
        ]
        if vals_list:
            self.create(vals_list)

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "budget_appropriation_onboarding."
            "action_budget_appropriation_onboarding"
        )
        action["context"] = {"search_default_current_fiscal_year": 1}
        return action

    def action_open_appropriations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ประมาณการรายรับ-รายจ่าย"),
            "res_model": "budget.appropriation",
            "view_mode": "tree,form",
            "domain": [
                (
                    "account_fiscal_year_id",
                    "=",
                    self.account_fiscal_year_id.id,
                ),
                (
                    "department_analytic_id",
                    "=",
                    self.department_analytic_id.id,
                ),
            ],
            "context": {
                "default_account_fiscal_year_id": (
                    self.account_fiscal_year_id.id
                ),
                "default_department_analytic_id": (
                    self.department_analytic_id.id
                ),
            },
        }

    def action_open_compilations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รวมเล่มหน่วยงาน"),
            "res_model": "budget.appropriation.compilation",
            "view_mode": "tree,form",
            "domain": [
                (
                    "account_fiscal_year_id",
                    "=",
                    self.account_fiscal_year_id.id,
                ),
                (
                    "department_analytic_id",
                    "=",
                    self.department_analytic_id.id,
                ),
            ],
            "context": {
                "default_account_fiscal_year_id": (
                    self.account_fiscal_year_id.id
                ),
                "default_department_analytic_id": (
                    self.department_analytic_id.id
                ),
            },
        }
