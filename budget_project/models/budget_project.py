import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class BudgetProject(models.Model):
    _name = "budget.project"
    _description = "Budget Project Reservation"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(
        string="ชื่อโครงการ/กิจกรรม",
        required=True,
        tracking=True,
    )
    budget_amount = fields.Float(
        string="งบประมาณ",
        digits="Product Price",
        tracking=True,
    )
    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        tracking=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
    )
    analytic_distribution = fields.Json(string="Analytic Distribution")

    # Analytic dimension fields for UI (computed from analytic_distribution)
    activity_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_ids",
        inverse="_inverse_activity_analytic_id",
        store=False,
        domain=[("root_plan_id.code", "=", "activities")],
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_ids",
        inverse="_inverse_department_analytic_id",
        store=False,
        domain=[("root_plan_id.code", "=", "departments")],
    )
    fund_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_ids",
        inverse="_inverse_fund_analytic_id",
        store=False,
        domain=[("root_plan_id.code", "=", "funds")],
    )
    source_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_ids",
        inverse="_inverse_source_analytic_id",
        store=False,
        domain=[("root_plan_id.code", "=", "sources")],
    )

    project_type = fields.Selection(
        [("project", "Project/Activity"), ("strategic_project", "Strategic Project")],
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้รับผิดชอบ",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        tracking=True,
    )
    is_matched = fields.Boolean(
        string="เชื่อมโยงแล้ว",
        compute="_compute_is_matched",
        store=True,
    )
    budget_move_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="budget_project_id",
        string="Budget Move Lines",
    )

    @api.depends("kmitl_project_id")
    def _compute_is_matched(self):
        for rec in self:
            rec.is_matched = bool(rec.kmitl_project_id)

    @api.depends("analytic_distribution")
    def _compute_analytic_ids(self):
        """Compute analytic_id fields from analytic_distribution JSON."""
        for rec in self:
            account_ids = [int(account_id) for account_id in rec.analytic_distribution or {}]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            rec.activity_analytic_id = accounts.filtered(lambda a: a.root_plan_id.code == "activities")[:1]
            rec.department_analytic_id = accounts.filtered(lambda a: a.root_plan_id.code == "departments")[:1]
            rec.fund_analytic_id = accounts.filtered(lambda a: a.root_plan_id.code == "funds")[:1]
            rec.source_analytic_id = accounts.filtered(lambda a: a.root_plan_id.code == "sources")[:1]

    def _update_analytic_distribution(self, plan_code, analytic_id):
        """Update analytic_distribution JSON when individual field changes."""
        self.ensure_one()
        distribution = dict(self.analytic_distribution or {})

        # Remove old account for this plan
        account_ids = [int(aid) for aid in distribution.keys()]
        accounts = self.env["account.analytic.account"].browse(account_ids)
        for account in accounts.filtered(lambda a: a.root_plan_id.code == plan_code):
            del distribution[str(account.id)]

        # Add new account
        if analytic_id:
            distribution[str(analytic_id.id)] = 100

        self.analytic_distribution = distribution if distribution else False

    def _inverse_activity_analytic_id(self):
        for rec in self:
            rec._update_analytic_distribution("activities", rec.activity_analytic_id)

    def _inverse_department_analytic_id(self):
        for rec in self:
            rec._update_analytic_distribution("departments", rec.department_analytic_id)

    def _inverse_fund_analytic_id(self):
        for rec in self:
            rec._update_analytic_distribution("funds", rec.fund_analytic_id)

    def _inverse_source_analytic_id(self):
        for rec in self:
            rec._update_analytic_distribution("sources", rec.source_analytic_id)

    def write(self, vals):
        res = super().write(vals)
        if "kmitl_project_id" in vals and vals["kmitl_project_id"]:
            for rec in self:
                rec._on_match_project()
        return res

    def _on_match_project(self):
        """Called when kmitl_project_id is set. Performs budget linking."""
        self.ensure_one()
        project = self.kmitl_project_id

        # 1. Copy budget data to kmitl.project
        project.write({
            "budget_account_id": self.budget_account_id.id,
            "budget_amount": self.budget_amount,
            "analytic_distribution": self.analytic_distribution,
        })

        # 2. Create analytic_account_id on kmitl.project if not exists
        if not project.analytic_account_id:
            analytic_account = self.env["account.analytic.account"].create({
                "name": project.name,
                "company_id": project.company_id.id,
                "plan_id": self.env.ref(
                    "kmitl_project.analytic_plan_project"
                ).id,
            })
            project.analytic_account_id = analytic_account.id

        # 3. Inject analytic_account_id into budget.move.line.analytic_distribution
        for move_line in self.budget_move_line_ids:
            distribution = dict(move_line.analytic_distribution or {})
            distribution[str(project.analytic_account_id.id)] = 100
            move_line.analytic_distribution = distribution
            move_line.project_id = project.id

        # 4. Post chatter messages
        self._post_match_messages()

    def _post_match_messages(self):
        """Post cross-link chatter messages on both records."""
        self.ensure_one()
        project = self.kmitl_project_id

        # Message on budget.project
        project_url = project._get_record_url()
        self.message_post(
            body=_(
                'เชื่อมโยงกับโครงการ/กิจกรรม: <a href="%(link)s" target="_blank">%(name)s</a>',
                link=project_url,
                name=project.name,
            ),
            message_type="comment",
        )

        # Message on kmitl.project
        reservation_url = self._get_record_url()
        project.message_post(
            body=_(
                'เชื่อมโยงกับการกันเงิน: <a href="%(link)s" target="_blank">%(name)s</a>',
                link=reservation_url,
                name=self.name,
            ),
            message_type="comment",
        )

    def action_create_kmitl_project(self):
        """Create a kmitl.project from this reservation and link it."""
        self.ensure_one()
        project = self.env["kmitl.project"].create({
            "name": self.name,
            "project_type": self.project_type or "project",
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "budget_account_id": self.budget_account_id.id,
            "budget_amount": self.budget_amount,
            "user_id": self.user_id.id if self.user_id else self.env.user.id,
            "creating_user_id": self.env.user.id,
            "company_id": self.company_id.id,
            "analytic_distribution": self.analytic_distribution,
        })
        self.kmitl_project_id = project.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "res_id": project.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)
