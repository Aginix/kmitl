import logging

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BudgetPlan(models.Model):
    _name = "budget.plan"
    _description = "Budget Plan"
    _inherit = ["mail.thread"]

    name = fields.Char(tracking=True)
    template_id = fields.Many2one(
        comodel_name="budget.template", ondelete="restrict", tracking=True
    )
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        store=True,
        related="template_id.date_range_fy_id",
        search="_search_date_range_fy",
    )
    note = fields.Text("Internal Notes", tracking=True)
    budget_type = fields.Selection(
        related="template_id.budget_type",
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        string="Responsible user",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        store=True,
        readonly=False,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        store=True,
        readonly=False,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        store=True,
        readonly=False,
    )
    line_ids = fields.One2many(
        comodel_name="budget.plan.line",
        inverse_name="plan_id",
        copy=True,
        tracking=True,
    )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)

        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain


class BudgetPlanLine(models.Model):
    _name = "budget.plan.line"
    _description = "Budget Plan Line"
    _inherit = ["mail.thread", "analytic.distribution.mixin"]

    code = fields.Char(related="template_line_id.code")
    name = fields.Char(related="template_line_id.name")
    plan_id = fields.Many2one(
        comodel_name="budget.plan", ondelete="cascade", required=True
    )
    template_id = fields.Many2one(related="plan_id.template_id")
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        ondelete="restrict",
        domain="[('template_id', '=', template_id)]",
        required=True,
    )
    amount = fields.Float(tracking=True)
    department_analytic_id = fields.Many2one(related="plan_id.department_analytic_id")
    source_analytic_id = fields.Many2one(related="plan_id.source_analytic_id")
