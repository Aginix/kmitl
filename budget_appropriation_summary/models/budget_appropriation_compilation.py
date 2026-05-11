from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BudgetAppropriationCompilation(models.Model):
    _name = "budget.appropriation.compilation"
    _description = "Budget Appropriation Compilation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"
    _sql_constraints = [
        (
            "unique_department_source_fiscal_year",
            "UNIQUE(department_analytic_id, source_analytic_id, account_fiscal_year_id)",
            "มีข้อมูลรวมเล่มงบประมาณของหน่วยงาน แหล่งเงิน และปีงบประมาณนี้อยู่แล้ว",
        ),
    ]

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "done": [("readonly", True)],
    }

    sequence = fields.Integer(string="ลำดับ", default=10)
    name = fields.Char(
        string="ชื่อรวมเล่ม",
        compute="_compute_name",
        store=True,
        readonly=True,
        tracking=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    source_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    revenue_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        relation="budget_appropriation_compilation_revenue_rel",
        column1="compilation_id",
        column2="appropriation_id",
        string="ประมาณการรายรับ",
        domain=[("budget_type", "=", "revenue")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    expense_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        relation="budget_appropriation_compilation_expense_rel",
        column1="compilation_id",
        column2="appropriation_id",
        string="ประมาณการรายจ่าย",
        domain=[("budget_type", "=", "expense")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="รายการจัดสรรทั้งหมด",
        compute="_compute_appropriation_ids",
        store=False,
    )
    amount_revenue_total = fields.Monetary(
        string="รายรับรวม",
        compute="_compute_amount_totals",
        store=True,
        currency_field="currency_id",
    )
    amount_expense_total = fields.Monetary(
        string="รายจ่ายรวม",
        compute="_compute_amount_totals",
        store=True,
        currency_field="currency_id",
    )
    master_summary_id = fields.Many2one(
        comodel_name="budget.appropriation.master.summary",
        string="สรุปภาพรวมสถาบัน",
        readonly=False,
        states=READONLY_STATES,
        ondelete="set null",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ],
        string="สถานะ",
        required=True,
        default="draft",
        tracking=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        readonly=False,
    )
    f4_revenue_data = fields.Json(
        string="F4 Revenue Data",
        compute="_compute_f4_revenue_data",
        store=False,
    )
    f5_expense_data = fields.Json(
        string="F5 Expense Data",
        compute="_compute_f5_expense_data",
        store=False,
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created by",
        default=lambda self: self.env.user,
        readonly=True,
    )

    use_f23 = fields.Boolean(
        string="ใช้รายงาน F23",
        help="ถ้าเลือก จะแสดงแบบฟอร์มรายงาน F23 ให้ผู้ใช้กรอกข้อมูลเพิ่มเติม",
        states=READONLY_STATES,
        readonly=False,
    )

    treasury_replenishment_amount = fields.Monetary(
        string="ชดใช้เงินคงคลัง",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    deducted_reserve_amount = fields.Monetary(
        string="หักเงินสำรอง",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    maintenance_amount = fields.Monetary(
        string="ค่าดูแลและบำรุงรักษา",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    capital_budget_amount = fields.Monetary(
        string="งบลงทุน",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    recurrent_budget_amount = fields.Monetary(
        string="งบประจำ",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    external_funding_amount = fields.Monetary(
        string="เงินสนับสนุนจากหน่วยงานภายนอก",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    revenue_net = fields.Monetary(
        string="รายรับรวมหลังหักโอน",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    fixed_expense_total = fields.Monetary(
        string="รายจ่ายคงที่",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    fixed_expense_percentage = fields.Monetary(
        string="รายจ่ายคงที่ (ร้อยละ)",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    code_0702000002 = fields.Monetary(
        string="สำรองจ่ายร้อยละ 15",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    code_0702000003 = fields.Monetary(
        string="สำรองจ่าย เกินกว่าร้อยละ 15",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    # Budget summary by expense type (aggregated from appropriations)
    reserve_fund_amount = fields.Monetary(
        string="งบกองทุนสำรอง",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    personnel_expense_amount = fields.Monetary(
        string="งบบุคลากร",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    operating_expense_amount = fields.Monetary(
        string="งบดำเนินงาน",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    capital_expenditure_amount = fields.Monetary(
        string="งบลงทุน",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    subsidy_amount = fields.Monetary(
        string="งบเงินอุดหนุน",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    other_expenditure_amount = fields.Monetary(
        string="งบรายจ่ายอื่น",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )

    education_impact_line_ids = fields.One2many(
        "budget.appropriation.compilation.impact",
        "compilation_id",
        string="รายการสัดส่วนผลกระทบ (การศึกษา)",
        domain=[("impact_type", "=", "education")],
        readonly=False,
        states=READONLY_STATES,
    )

    education_impact_total = fields.Float(compute="_compute_impact_totals", store=False)
    education_total = fields.Monetary(compute="_compute_impact_totals", store=False, currency_field="currency_id")
    education_okr_percentage = fields.Float(compute="_compute_impact_totals", store=False)
    education_mgt_percentage = fields.Float(compute="_compute_impact_totals", store=False)

    academic_impact_line_ids = fields.One2many(
        "budget.appropriation.compilation.impact",
        "compilation_id",
        string="รายการสัดส่วนผลกระทบ (การวิจัย)",
        domain=[("impact_type", "=", "academic")],
        readonly=False,
        states=READONLY_STATES,
    )

    academic_impact_total = fields.Float(compute="_compute_impact_totals", store=False)
    academic_total = fields.Monetary(compute="_compute_impact_totals", store=False, currency_field="currency_id")
    academic_okr_percentage = fields.Float(compute="_compute_impact_totals", store=False)
    academic_mgt_percentage = fields.Float(compute="_compute_impact_totals", store=False)

    industrial_impact_line_ids = fields.One2many(
        "budget.appropriation.compilation.impact",
        "compilation_id",
        string="รายการสัดส่วนผลกระทบ (อุตสาหกรรม)",
        domain=[("impact_type", "=", "industrial")],
        readonly=False,
        states=READONLY_STATES,
    )

    industrial_impact_total = fields.Float(compute="_compute_impact_totals", store=False)
    industrial_total = fields.Monetary(compute="_compute_impact_totals", store=False, currency_field="currency_id")
    industrial_okr_percentage = fields.Float(compute="_compute_impact_totals", store=False)
    industrial_mgt_percentage = fields.Float(compute="_compute_impact_totals", store=False)

    social_impact_line_ids = fields.One2many(
        "budget.appropriation.compilation.impact",
        "compilation_id",
        string="รายการสัดส่วนผลกระทบ (สังคม)",
        domain=[("impact_type", "=", "social")],
        readonly=False,
        states=READONLY_STATES,
    )

    social_impact_total = fields.Float(compute="_compute_impact_totals", store=False)
    social_total = fields.Monetary(compute="_compute_impact_totals", store=False, currency_field="currency_id")
    social_okr_percentage = fields.Float(compute="_compute_impact_totals", store=False)
    social_mgt_percentage = fields.Float(compute="_compute_impact_totals", store=False)

    @api.depends(
        "expense_appropriation_ids.treasury_replenishment_amount",
        "expense_appropriation_ids.deducted_reserve_amount",
        "expense_appropriation_ids.maintenance_amount",
        "expense_appropriation_ids.capital_budget_amount",
        "expense_appropriation_ids.recurrent_budget_amount",
        "expense_appropriation_ids.external_funding_amount",
        "expense_appropriation_ids.code_0702000002",
        "expense_appropriation_ids.code_0702000003",
        "revenue_appropriation_ids.amount_net",
    )
    def _compute_totals(self):
        for record in self:
            record.treasury_replenishment_amount = sum(
                record.expense_appropriation_ids.mapped("treasury_replenishment_amount")
            )
            record.deducted_reserve_amount = sum(
                record.expense_appropriation_ids.mapped("deducted_reserve_amount")
            )
            record.maintenance_amount = sum(
                record.expense_appropriation_ids.mapped("maintenance_amount")
            )
            record.capital_budget_amount = sum(
                record.expense_appropriation_ids.mapped("capital_budget_amount")
            )
            record.recurrent_budget_amount = sum(
                record.expense_appropriation_ids.mapped("recurrent_budget_amount")
            )
            record.external_funding_amount = sum(
                record.expense_appropriation_ids.mapped("external_funding_amount")
            )
            record.revenue_net = sum(
                record.revenue_appropriation_ids.mapped("amount_net")
            )
            record.code_0702000002 = sum(
                record.expense_appropriation_ids.mapped("code_0702000002")
            )
            record.code_0702000003 = sum(
                record.expense_appropriation_ids.mapped("code_0702000003")
            )
            record.fixed_expense_total = sum([
                record.treasury_replenishment_amount,
                record.deducted_reserve_amount,
                record.maintenance_amount,
                record.capital_budget_amount,
                record.recurrent_budget_amount,
                record.external_funding_amount
            ])

            record.fixed_expense_percentage = (record.fixed_expense_total * 100) / record.revenue_net if record.revenue_net else 0.0

    BUDGET_SUMMARY_FIELDS = [
        "reserve_fund_amount",
        "personnel_expense_amount",
        "operating_expense_amount",
        "capital_expenditure_amount",
        "subsidy_amount",
        "other_expenditure_amount",
    ]

    @api.depends(
        "expense_appropriation_ids.reserve_fund_amount",
        "expense_appropriation_ids.personnel_expense_amount",
        "expense_appropriation_ids.operating_expense_amount",
        "expense_appropriation_ids.capital_expenditure_amount",
        "expense_appropriation_ids.subsidy_amount",
        "expense_appropriation_ids.other_expenditure_amount",
    )
    def _compute_budget_summary_amounts(self):
        for record in self:
            for field_name in self.BUDGET_SUMMARY_FIELDS:
                record[field_name] = sum(
                    record.expense_appropriation_ids.mapped(field_name)
                )

    @api.depends(
        "education_impact_line_ids.project_okr_amount",
        "education_impact_line_ids.management_amount",
        "academic_impact_line_ids.project_okr_amount",
        "academic_impact_line_ids.management_amount",
        "industrial_impact_line_ids.project_okr_amount",
        "industrial_impact_line_ids.management_amount",
        "social_impact_line_ids.project_okr_amount",
        "social_impact_line_ids.management_amount",
    )
    def _compute_impact_totals(self):
        impact_line_fields = {
            "education": "education_impact_line_ids",
            "academic": "academic_impact_line_ids",
            "industrial": "industrial_impact_line_ids",
            "social": "social_impact_line_ids",
        }
        for record in self:
            totals = {}
            grand_total = 0
            for itype, field in impact_line_fields.items():
                lines = record[field]
                okr = sum(lines.mapped("project_okr_amount"))
                mgmt = sum(lines.mapped("management_amount"))
                total = okr + mgmt
                totals[itype] = {"okr": okr, "mgmt": mgmt, "total": total}
                grand_total += total
            for itype in impact_line_fields:
                t = totals[itype]
                record[f"{itype}_total"] = t["total"]
                record[f"{itype}_impact_total"] = (t["total"] * 100 / grand_total) if grand_total else 0
                record[f"{itype}_okr_percentage"] = (t["okr"] * 100 / grand_total) if grand_total else 0
                record[f"{itype}_mgt_percentage"] = (t["mgmt"] * 100 / grand_total) if grand_total else 0

    @api.depends(
        "department_analytic_id",
        "source_analytic_id",
        "account_fiscal_year_id",
    )
    def _compute_name(self):
        for record in self:
            department = record.department_analytic_id.complete_name
            if department:
                department = department.replace(" / ", " ")
            record.name = _("%s (%s) ปีงบประมาณ พ.ศ. %s") % (
                department or "",
                record.source_analytic_id.name or "",
                record.account_fiscal_year_id.name or "",
            )

    @api.depends("revenue_appropriation_ids", "expense_appropriation_ids")
    def _compute_appropriation_ids(self):
        for record in self:
            record.appropriation_ids = (
                record.revenue_appropriation_ids | record.expense_appropriation_ids
            )

    @api.depends(
        "revenue_appropriation_ids.amount_net",
        "expense_appropriation_ids.amount_net",
    )
    def _compute_amount_totals(self):
        for record in self:
            record.amount_revenue_total = sum(
                record.revenue_appropriation_ids.mapped("amount_net")
            )
            record.amount_expense_total = sum(
                record.expense_appropriation_ids.mapped("amount_net")
            )

    @api.depends("revenue_appropriation_ids")
    def _compute_f4_revenue_data(self):
        F4Model = self.env["budget.appropriation.f4.report"]
        for record in self:
            if not record.revenue_appropriation_ids:
                record.f4_revenue_data = {}
                continue
            apps = record.revenue_appropriation_ids
            if len(apps) == 1:
                record.f4_revenue_data = {"details": [F4Model.get_f4_data(apps.id)]}
            else:
                dept_name = (record.department_analytic_id.complete_name or "").replace(
                    " / ", " "
                )
                overview = F4Model.get_f4_data(
                    apps.ids,
                    {"department_name": f"{dept_name} (ภาพรวม)"},
                )
                details = []
                for app in apps.sorted(lambda a: a.department_analytic_id.code or ""):
                    details.append(F4Model.get_f4_data(app.id))
                record.f4_revenue_data = {"overview": overview, "details": details}

    @api.depends("expense_appropriation_ids")
    def _compute_f5_expense_data(self):
        F5Model = self.env["budget.appropriation.f5.report"]
        for record in self:
            if not record.expense_appropriation_ids:
                record.f5_expense_data = {}
                continue
            apps = record.expense_appropriation_ids
            if len(apps) == 1:
                data = {"details": [F5Model.get_f5_data(apps.id)]}
            else:
                dept_name = (record.department_analytic_id.complete_name or "").replace(
                    " / ", " "
                )
                overview = F5Model.get_f5_data(
                    apps.ids,
                    {"department_name": f"{dept_name} (ภาพรวม)"},
                )
                details = []
                for app in apps.sorted(lambda a: a.department_analytic_id.code or ""):
                    details.append(F5Model.get_f5_data(app.id))
                data = {"overview": overview, "details": details}
            record.f5_expense_data = self._merge_f5_last_level_nodes(data)

    @api.model
    def _merge_f5_last_level_nodes(self, data):
        """Merge last-level account nodes with the same id for non-itemized mode."""

        def merge_children(nodes, clear_text=False):
            merged = []
            seen = {}
            for node in nodes:
                if node.get("children"):
                    node["children"] = merge_children(
                        node["children"], clear_text=clear_text
                    )
                # Merge leaf account nodes (no children) by id
                if (
                    node.get("type") == "account"
                    and not node.get("children")
                ):
                    key = node.get("id")
                    if key in seen:
                        existing = seen[key]
                        existing["amount"] = existing.get("amount", 0) + node.get(
                            "amount", 0
                        )
                        existing["amount_total"] = existing.get(
                            "amount_total", 0
                        ) + node.get("amount_total", 0)
                    else:
                        if clear_text:
                            node["description"] = ""
                            node["note"] = ""
                        seen[key] = node
                        merged.append(node)
                else:
                    merged.append(node)
            return merged

        for key in ("overview", "details"):
            if key == "details":
                for detail in data.get("details", []):
                    if detail.get("hierarchy"):
                        detail["hierarchy"] = merge_children(
                            detail["hierarchy"], clear_text=False
                        )
            elif key == "overview" and data.get("overview"):
                overview = data["overview"]
                if overview.get("hierarchy"):
                    overview["hierarchy"] = merge_children(
                        overview["hierarchy"], clear_text=True
                    )
        return data

    def action_confirm(self):
        for record in self:
            not_ready = (
                record.revenue_appropriation_ids + record.expense_appropriation_ids
            ).filtered(lambda a: a.state not in ("review", "posted"))
            if not_ready:
                names = ", ".join(not_ready.mapped("name"))
                raise ValidationError(
                    _(
                        "ไม่สามารถยืนยันรวมเล่มได้ เนื่องจากรายการจัดสรรต่อไปนี้ยังไม่ได้อยู่ในสถานะ review หรือ posted:\n%s"
                    )
                    % names
                )
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_f4_report(self):
        """Open F4 revenue report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f4/html",
            "target": "new",
        }

    def get_f5_expense_data_with_options(self, options=None):
        """Generate F5 expense data with display options.

        Args:
            options: dict with keys:
                - show_itemized (bool): show individual budget code lines
        """
        self.ensure_one()
        if options is None:
            options = {}
        F5Model = self.env["budget.appropriation.f5.report"]
        if not self.expense_appropriation_ids:
            return {}
        apps = self.expense_appropriation_ids
        show_itemized = options.get("show_itemized", False)
        f5_options = {"show_itemized": show_itemized}
        if len(apps) == 1:
            data = {"details": [F5Model.get_f5_data(apps.id, f5_options)]}
        else:
            dept_name = (self.department_analytic_id.complete_name or "").replace(
                " / ", " "
            )
            f5_options["department_name"] = f"{dept_name} (ภาพรวม)"
            overview = F5Model.get_f5_data(apps.ids, f5_options)
            details = []
            detail_options = {"show_itemized": show_itemized}
            for app in apps.sorted(lambda a: a.department_analytic_id.code or ""):
                details.append(F5Model.get_f5_data(app.id, detail_options))
            data = {"overview": overview, "details": details}
        if not show_itemized:
            data = self._merge_f5_last_level_nodes(data)
        return data

    def action_open_f5_report(self):
        """Open wizard for F5 expense report options."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.appropriation.compilation.f5.print.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def action_print_f4_report(self):
        """Print F4 revenue report as PDF."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_summary.action_report_compilation_f4"
        ).report_action(self)

    def action_print_f5_report(self):
        """Open wizard for F5 expense report options."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.appropriation.compilation.f5.print.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def get_impact_line_hierarchy(self, impact_type=None, min_level=3):
        """Build flattened hierarchy from impact lines for F23W report display.

        Returns dict with rows containing project_okr_amount and management_amount.
        Totals are flat sums of all lines (no bubble-up) to avoid double-counting.
        Rows show direct amounts only — parent rows do not include children's amounts.
        """
        self.ensure_one()
        lines = self.env["budget.appropriation.compilation.impact"].search([
            ("compilation_id", "=", self.id),
            ("impact_type", "=", impact_type),
        ]) if impact_type else self.env["budget.appropriation.compilation.impact"]

        if not lines:
            return {"rows": [], "total_project_okr": 0, "total_management": 0}

        # Flat sums — no hierarchy, no double-counting
        total_project_okr = sum(lines.mapped("project_okr_amount"))
        total_management = sum(lines.mapped("management_amount"))

        # Build account set including ancestors for hierarchy display
        analytic_accounts = lines.mapped("analytic_account_id")
        all_account_ids = set()
        for account in analytic_accounts:
            if account.parent_path:
                parent_ids = [
                    int(pid)
                    for pid in account.parent_path.strip("/").split("/")
                    if pid
                ]
                all_account_ids.update(parent_ids)
            all_account_ids.add(account.id)

        accounts = self.env["account.analytic.account"].browse(list(all_account_ids))

        account_levels = {}
        for acc in accounts:
            if acc.parent_path:
                level = len(
                    [p for p in acc.parent_path.strip("/").split("/") if p]
                )
            else:
                level = 1
            account_levels[acc.id] = level

        # Direct amounts per account only (no bubble-up to avoid double-counting)
        direct_amounts = {}
        for line in lines:
            acc_id = line.analytic_account_id.id
            if acc_id not in direct_amounts:
                direct_amounts[acc_id] = {"project_okr_amount": 0, "management_amount": 0}
            direct_amounts[acc_id]["project_okr_amount"] += line.project_okr_amount
            direct_amounts[acc_id]["management_amount"] += line.management_amount

        rows = []

        # Sort by 2-char prefix priority (09 first, then 06, then others), code asc
        _prefix_order = {"09": 0, "06": 1}

        def _sort_key(a):
            code = a.code or ""
            return (_prefix_order.get(code[:2], 99), code)

        def flatten_node(account, display_level):
            acc_level = account_levels.get(account.id, 1)
            if acc_level >= min_level:
                amounts = direct_amounts.get(account.id, {"project_okr_amount": 0, "management_amount": 0})
                rows.append({
                    "type": "account",
                    "level": display_level,
                    "code": account.code or "",
                    "name": account.name,
                    "project_okr_amount": amounts["project_okr_amount"],
                    "management_amount": amounts["management_amount"],
                })
            child_accounts = sorted(
                [a for a in accounts if a.parent_id and a.parent_id.id == account.id],
                key=_sort_key,
            )
            for child in child_accounts:
                next_level = display_level + 1 if acc_level >= min_level else display_level
                flatten_node(child, next_level)

        root_accounts = sorted(
            [a for a in accounts if not a.parent_id or a.parent_id.id not in all_account_ids],
            key=_sort_key,
        )
        for root in root_accounts:
            flatten_node(root, 0)

        return {
            "rows": rows,
            "total_project_okr": total_project_okr,
            "total_management": total_management,
        }

    _F23W_IMPACT_TYPES = [
        ("education", "1) ด้านการศึกษา (Education)"),
        ("academic", "2) ด้านการวิจัย (Academic)"),
        ("industrial", "3) ด้านตอบโจทย์ภาคอุตสาหกรรม (Industrial)"),
        ("social", "4) ด้านสังคม (Social)"),
    ]

    def get_f23w_report_data(self):
        """Prepare F23W report rows for QWeb rendering.

        Returns a flat list of row dicts with a ``type`` key that tells
        the QWeb template how to render each row.
        """
        self.ensure_one()

        # Pre-compute impact data and grand totals
        impact_data = []
        for itype, ilabel in self._F23W_IMPACT_TYPES:
            data = self.get_impact_line_hierarchy(itype)
            impact_data.append((itype, ilabel, data))

        grand_okr = sum(d[2].get("total_project_okr", 0) for d in impact_data)
        grand_mgmt = sum(d[2].get("total_management", 0) for d in impact_data)
        grand_total = grand_okr + grand_mgmt
        variable_pct = (
            (grand_total * 100 / self.revenue_net) if self.revenue_net else 0
        )

        rows = []

        # --- Section 1: Fixed expenses ---
        rows.append({"type": "fixed_header"})
        rows.append({"type": "data", "label": "1. หักสำรองจ่าย"})
        rows.append({
            "type": "data",
            "label": "1.1 สำรองจ่ายร้อยละ 15",
            "amount": self.code_0702000002,
            "indent": True,
        })
        rows.append({
            "type": "data",
            "label": "1.2 สำรองจ่ายเกินกว่าร้อยละ 15",
            "amount": self.code_0702000003,
            "indent": True,
        })
        rows.append({
            "type": "data",
            "label": "2. ชดใช้เงินคงคลัง (ถ้ามี)",
            "amount": self.treasury_replenishment_amount,
        })
        rows.append({
            "type": "data_multiline",
            "label": "3. ค่าดูแลและบำรุงรักษา",
            "label2": "(Preventive Maintenance บำรุงรักษาเชิงป้องกัน)",
            "amount": self.maintenance_amount,
        })
        rows.append({
            "type": "data",
            "label": "4. งบลงทุน",
            "amount": self.capital_budget_amount,
        })
        rows.append({
            "type": "data",
            "label": "5. งบประจำ",
            "amount": self.recurrent_budget_amount,
        })
        rows.append({
            "type": "data",
            "label": "6. เงินสนับสนุนจากหน่วยงานภายนอก",
            "amount": self.external_funding_amount,
        })
        rows.append({
            "type": "fixed_total",
            "pct": self.fixed_expense_percentage,
            "amount": self.fixed_expense_total,
        })

        # --- Section 2: Impact types ---
        rows.append({"type": "spacer"})
        rows.append({
            "type": "impact_section_header",
            "pct": variable_pct,
            "amount": grand_total,
        })
        rows.append({"type": "impact_column_header"})

        for _itype, ilabel, idata in impact_data:
            i_okr = idata.get("total_project_okr", 0)
            i_mgmt = idata.get("total_management", 0)
            i_total = i_okr + i_mgmt
            rows.append({
                "type": "impact_type_header",
                "label": ilabel,
                "pct": (i_total * 100 / grand_total) if grand_total else 0,
                "okr_pct": (i_okr * 100 / grand_total) if grand_total else 0,
                "mgmt_pct": (i_mgmt * 100 / grand_total) if grand_total else 0,
                "amount": i_total,
            })
            for row in idata.get("rows", []):
                rows.append({
                    "type": "impact_row",
                    "name": row.get("name", ""),
                    "level": row.get("level", 0),
                    "okr_amount": row.get("project_okr_amount", 0),
                    "mgmt_amount": row.get("management_amount", 0),
                })
            rows.append({"type": "spacer"})

        # --- Section 3: Grand totals ---
        okr_pct = (grand_okr * 100 / grand_total) if grand_total else 0
        mgmt_pct = (grand_mgmt * 100 / grand_total) if grand_total else 0
        rows.append({
            "type": "sub_totals",
            "okr_pct": okr_pct,
            "mgmt_pct": mgmt_pct,
        })
        rows.append({
            "type": "grand_total_line",
            "okr_amount": grand_okr,
            "mgmt_amount": grand_mgmt,
            "amount": grand_total,
        })
        rows.append({
            "type": "grand_total",
            "amount": self.fixed_expense_total + grand_total,
        })

        return rows

    def action_open_f23w_report(self):
        """Open F23W report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f23w/html",
            "target": "new",
        }

    def action_print_f23w_report(self):
        """Print F23W report as PDF."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_summary.action_report_compilation_f23w"
        ).report_action(self)
