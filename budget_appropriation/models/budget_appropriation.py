import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    """
    Budget Appropriation - Draft appropriations before creating budget moves.

    Business Purpose:
        Budget appropriations serve as draft budget allocations that can be
        reviewed and modified before being posted as budget moves. This provides
        a preliminary stage for budget planning without affecting the actual
        budget accounts through double-entry accounting.

    Key Differences from Budget Move:
        • No double-entry accounting - simple appropriation tracking
        • Can be extensively modified in draft state
        • Creates budget moves only after approval
        • Focuses on appropriation planning rather than accounting entries

    State Lifecycle:
        draft → review → posted → cancel
        │       │        │        │
        │       │        │        └── Cancelled, no budget impact
        │       │        └─────────── Creates budget.move entries
        │       └──────────────────── Under approval, locked from changes
        └──────────────────────────── Editable, no budget impact

    Integration with Budget System:
        • Creates budget.move entries when posted
        • Maintains link to created budget moves
        • Provides appropriation history and audit trail
    """

    _name = "budget.appropriation"
    _description = "Budget Appropriation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    READONLY_STATES = {
        "review": [("readonly", True)],
        "posted": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="รายการ",
        compute="_compute_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    ref = fields.Char(
        string="Reference",
        copy=False,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    date = fields.Date(
        string="วันที่",
        index=True,
        default=lambda self: fields.Date.context_today(self),
        required=True,
        readonly=False,
        copy=False,
        tracking=True,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("review", "In Review"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="สถานะ",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    note = fields.Text(
        readonly=False,
        tracking=True,
        states=READONLY_STATES,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        store=True,
        copy=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        store=True,
        copy=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[("root_plan_id.code", "=", "sources")],
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one(
        string="Responsible user",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        store=True,
        readonly=False,
        states=READONLY_STATES,
    )
    line_ids = fields.One2many(
        comodel_name="budget.appropriation.line",
        inverse_name="appropriation_id",
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[('deduct', '=', False)],
    )
    deduct_line_ids = fields.One2many(
        comodel_name="budget.appropriation.line",
        inverse_name="appropriation_id",
        copy=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
        domain=[('deduct', '=', True)],
    )
    budget_type = fields.Selection(
        [("revenue", "Revenue"), ("expense", "Expense")],
        string="Budget Type",
        required=True,
        copy=True,
        default="expense",
        states=READONLY_STATES,
    )
    appropriation_type = fields.Selection(
        selection=[
            ("initial", "งบประมาณต้นปี"),
            ("supplementary", "งบประมาณเพิ่มเติม"),
        ],
        string="ประเภทการจัดสรร",
        tracking=True,
        copy=True,
        default="initial",
        readonly=False,
        states=READONLY_STATES,
        help="ใช้แยกประเภทการจัดสรรงบประมาณ ต้นปี vs ระหว่างปี",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Account Currency",
        default=lambda self: self.env.company.currency_id,
        tracking=True,
        store=True,
        required=True,
    )
    company_currency_id = fields.Many2one(related="company_id.currency_id")
    amount_total = fields.Float(
        string="งบประมาณทั้งหมด",
        compute="_compute_amount",
        readonly=True,
        store=True,
        digits="Budget Precision",
    )
    amount_deduct = fields.Float(
        string="Deduct",
        compute="_compute_amount",
        readonly=True,
        store=True,
        digits="Budget Precision",
    )
    amount_net = fields.Float(
        string="Amount Net",
        compute="_compute_amount",
        readonly=True,
        store=True,
        digits="Budget Precision",
    )

    # Budget summary by expense type
    BUDGET_SUMMARY_CODES = {
        "reserve_fund_amount": "07020",
        "personnel_expense_amount": "51000",
        "operating_expense_amount": "52000",
        "capital_expenditure_amount": "53000",
        "subsidy_amount": "54000",
        "other_expenditure_amount": "55000",
    }

    reserve_fund_amount = fields.Float(
        string="งบกองทุนสำรอง",
        compute="_compute_budget_summary_amounts",
        digits="Budget Precision",
    )
    personnel_expense_amount = fields.Float(
        string="งบบุคลากร",
        compute="_compute_budget_summary_amounts",
        digits="Budget Precision",
    )
    operating_expense_amount = fields.Float(
        string="งบดำเนินงาน",
        compute="_compute_budget_summary_amounts",
        digits="Budget Precision",
    )
    capital_expenditure_amount = fields.Float(
        string="งบลงทุน",
        compute="_compute_budget_summary_amounts",
        digits="Budget Precision",
    )
    subsidy_amount = fields.Float(
        string="งบเงินอุดหนุน",
        compute="_compute_budget_summary_amounts",
        digits="Budget Precision",
    )
    other_expenditure_amount = fields.Float(
        string="งบรายจ่ายอื่น",
        compute="_compute_budget_summary_amounts",
        digits="Budget Precision",
    )

    # Link to created budget move
    budget_move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Created Budget Move",
        readonly=True,
        copy=False,
        help="Budget move created when this appropriation was posted",
    )

    # Display buttons
    show_reset_to_draft_button = fields.Boolean(
        compute="_compute_show_reset_to_draft_button"
    )
    hide_post_button = fields.Boolean(
        compute="_compute_hide_post_button", readonly=True
    )
    hide_review_button = fields.Boolean(
        compute="_compute_hide_review_button", readonly=True
    )

    # Portal: computed account_ids for hierarchy traversal
    account_ids = fields.Many2many(
        "budget.account",
        compute="_compute_account_ids",
        context={"active_test": False},
        string="Budget Accounts",
        help="Budget accounts computed from budget account hierarchy.",
    )

    @api.depends("line_ids.account_id")
    def _compute_account_ids(self):
        """Compute all budget accounts from line hierarchy."""
        for rec in self:
            all_account_ids = []
            for account_ids in rec.line_ids.mapped("account_ids"):
                all_account_ids += account_ids.mapped("id")
            for account_ids in rec.deduct_line_ids.mapped("account_ids"):
                all_account_ids += account_ids.mapped("id")
            rec.account_ids = [Command.set(list(set(all_account_ids)))]

    @api.depends("line_ids.balance", "deduct_line_ids.balance")
    def _compute_amount(self):
        for appropriation in self:
            amount_total = sum(appropriation.line_ids.mapped("balance"))
            amount_deduct = sum(appropriation.deduct_line_ids.mapped("balance"))
            appropriation.amount_total = amount_total
            appropriation.amount_deduct = amount_deduct
            appropriation.amount_net = amount_total - amount_deduct

    @api.depends("line_ids.balance", "line_ids.account_id")
    def _compute_budget_summary_amounts(self):
        # Build account_id -> field_name mapping in 2 queries instead of 12
        BudgetAccount = self.env["budget.account"]
        code_to_field = {v: k for k, v in self.BUDGET_SUMMARY_CODES.items()}
        parents = BudgetAccount.search(
            [("code", "in", list(code_to_field.keys()))]
        )
        account_field_map = {}
        if parents:
            domain = expression.OR(
                [("parent_path", "=like", f"{p.parent_path}%")]
                for p in parents
            )
            descendants = BudgetAccount.search(domain)
            # Map each descendant back to the parent code's field name
            for desc in descendants:
                for parent in parents:
                    if desc.parent_path.startswith(parent.parent_path):
                        account_field_map[desc.id] = code_to_field[parent.code]
                        break

        for record in self:
            totals = dict.fromkeys(self.BUDGET_SUMMARY_CODES, 0.0)
            for line in record.line_ids:
                field_name = account_field_map.get(line.account_id.id)
                if field_name:
                    totals[field_name] += line.balance
            for field_name, amount in totals.items():
                record[field_name] = amount

    @api.depends("state", "date")
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or "", m.id))

        for appropriation in self:
            if appropriation.state == "cancel":
                continue

            appropriation_has_name = appropriation.name and appropriation.name != _("New")
            if appropriation_has_name or (
                appropriation.state not in ("review", "posted")
            ):
                continue
            if not appropriation_has_name and appropriation.date:
                appropriation.name = self.env["ir.sequence"].next_by_code(
                    "budget.appropriation"
                ) or _("New")

    @api.depends("date", "state", "appropriation_type")
    def _compute_hide_post_button(self):
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        for record in self:
            if record.state != "review":
                record.hide_post_button = True
            elif not is_manager and record.appropriation_type == "initial":
                record.hide_post_button = True
            else:
                record.hide_post_button = False

    @api.depends("state")
    def _compute_hide_review_button(self):
        for record in self:
            record.hide_review_button = record.state != "draft"

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for record in self:
            record.show_reset_to_draft_button = record.state in (
                "review",
                "cancel",
            )

    def action_review(self):
        self.write({"state": "review"})

    def action_post(self):
        """Post appropriation and create budget move"""
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        if not is_manager:
            initial = self.filtered(lambda r: r.appropriation_type == "initial")
            if initial:
                raise UserError(
                    _(
                        "เฉพาะผู้จัดการงบประมาณเท่านั้นที่สามารถอนุมัติการจัดสรรงบประมาณต้นปีได้"
                    )
                )
        self._create_budget_move()
        self.write({"state": "posted"})

    def unlink(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(
                    _("ไม่สามารถลบรายการจัดสรรงบประมาณได้ กรุณายกเลิกรายการก่อนทำการลบ")
                )
        return super().unlink()

    def button_cancel(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    _("สามารถยกเลิกได้เฉพาะรายการที่อยู่ในสถานะ Draft เท่านั้น")
                )
        self.write({"state": "cancel"})

    def button_draft(self):
        # Reset to draft only if no budget move created
        for record in self:
            if record.budget_move_id and record.budget_move_id.state == "posted":
                raise UserError(
                    _("Cannot reset to draft: Related budget move is already posted.")
                )
        self.write({"state": "draft"})

    def _create_budget_move(self):
        """Create budget move from appropriation"""
        for appropriation in self:
            if appropriation.budget_move_id:
                continue  # Already created

            # Create budget move with essential fields
            move_vals = appropriation.budget_move_vals()

            budget_move = self.env["budget.move"].create(move_vals)
            appropriation.budget_move_id = budget_move.id

            # Auto-post the budget move
            budget_move.action_review()
            budget_move.action_post()

    def budget_move_vals(self):
        vals = {
            "move_type": "appropriation",
            "appropriation_type": self.appropriation_type,
            "date": self.date,
            "ref": self.ref,
            "department_analytic_id": self.department_analytic_id.id,
            "source_analytic_id": self.source_analytic_id.id,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "note": self.note,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "appropriation_id": self.id,
            "line_ids": [Command.create(vals) for vals in self.budget_move_line_vals()],
        }

        return vals

    def budget_move_line_vals(self):
        lines = list()
        for line in self.line_ids:
            lines.append(line.budget_move_line_vals())
        return lines

    def action_open_f5_preview(self):
        """Open the budget appropriation F5 preview in full screen"""
        self.ensure_one()
        return {
            "name": _("Budget Appropriation F5 Preview"),
            "type": "ir.actions.client",
            "tag": "budget_appropriation_f5_preview",
            "target": "current",
            "res_id": self.id,
            "res_model": "budget.appropriation",
            "context": {
                "active_id": self.id,
                "active_model": "budget.appropriation",
            },
        }

    def action_open_f4_preview(self):
        """Open the budget appropriation F4 preview for revenue in full screen"""
        self.ensure_one()
        return {
            "name": _("Budget Appropriation F4 Preview"),
            "type": "ir.actions.client",
            "tag": "budget_appropriation_f4_preview",
            "target": "current",
            "res_id": self.id,
            "res_model": "budget.appropriation",
            "context": {
                "active_id": self.id,
                "active_model": "budget.appropriation",
            },
        }

    def print_f5_pdf(self):
        self.ensure_one()
        return {
            "name": "พิมพ์ F5",
            "type": "ir.actions.act_window",
            "res_model": "budget.appropriation.f5.print.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_ids": self.ids, "active_model": self._name},
        }

    def open_record_url(self):
        """Open portal preview URL in new tab."""
        if self.id:
            return {
                'type': 'ir.actions.act_url',
                'url': '/budget/budget_appropriation/%s' % (self.id),
                'target': 'new',
            }

    def get_f4_report_data(self):
        """Generate F4 report data for portal display (revenue appropriations)."""
        self.ensure_one()
        root_account_ids = self.env["budget.account"].search(
            [
                ("parent_id", "=", False),
                ("id", "in", self.account_ids.mapped(lambda x: x.id)),
            ],
            order="code",
        )

        def _process_account(account_id, array, deduct):
            rows = self.deduct_line_ids if deduct else self.line_ids
            rows = rows.filtered(
                lambda x: x.account_id.parent_path.startswith(account_id.parent_path)
                or ("/" + account_id.parent_path) in x.account_id.parent_path
            )

            balance = sum(rows.mapped("balance"))

            if rows:
                array.append(
                    {
                        "id": account_id.id,
                        "code": account_id.code,
                        "name": account_id.name,
                        "hierarchy_level": account_id.hierarchy_level,
                        "balance": balance,
                        "sub_rows": [
                            {
                                "id": line.id,
                                "description": line.description,
                                "note": line.note,
                            }
                            for line in rows.filtered(
                                lambda x: x.account_id.id == account_id.id
                            )
                        ],
                    }
                )

            for child_id in account_id.child_ids:
                _process_account(child_id, array, deduct)

        line_ids = []
        for account_id in root_account_ids.filtered(lambda x: not x.deduct):
            _process_account(account_id, line_ids, False)

        deduct_ids = []
        for account_id in root_account_ids.filtered(lambda x: x.deduct):
            _process_account(account_id, deduct_ids, True)

        return {
            "id": self.id,
            "name": self.name,
            "account_fiscal_year": self.account_fiscal_year_id.name,
            "source_analytic_name": self.source_analytic_id.complete_name,
            "line_ids": line_ids,
            "deduct_ids": deduct_ids,
        }
