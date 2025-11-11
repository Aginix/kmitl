import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveRequest(models.Model):

    _name = "account.move.request"
    _inherit = ["account.move.request", "budget.commitment.mixin"]

    _commitment_id_field = "budget_commitment_id"
    _commitment_account_id_field = "budget_account_id"

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "validated": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        tracking=True,
        copy=False,
        states=READONLY_STATES,
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        tracking=True,
        copy=False,
        states=READONLY_STATES,
    )

    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        for rec in self:
            if rec.budget_commitment_id:
                budget = rec.budget_commitment_id
                rec.budget_account_id = budget.account_id
                rec.analytic_distribution = budget.analytic_distribution

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        search="_search_source_analytic_id",
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    @api.model
    def _search_source_analytic_id(self, operator, value):
        account_ids = []
        if type(value) == int:
            account_ids.append(value)
        else:
            account_ids = (
                self.env["account.analytic.account"]
                .search(
                    [
                        ("root_plan_id.code", "=", "sources"),
                        "|",
                        ("name", "ilike", value),
                        ("complete_name", "ilike", value),
                    ]
                )
                .mapped("id")
            )

        query = f"""
            SELECT id
            FROM {self._table}
            WHERE analytic_distribution ?| array[%s]
        """
        return [
            (
                "id",
                "inselect",
                (query, [[str(account_id) for account_id in account_ids]]),
            )
        ]

    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("sources")
