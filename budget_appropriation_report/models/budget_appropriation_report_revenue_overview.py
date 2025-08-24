# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationReportRevenueOverview(models.AbstractModel):
    _name = _description = "budget.appropriation.report.revenue.overview"

    @api.model
    def get_data(self):
        fiscal_year_id = 2
        state = "review"
        fiscal_year = self.env["account.fiscal.year"].browse(fiscal_year_id)

        accounts = self.env["budget.account"].search(
            [("budget_type", "=", "revenue"), ("parent_id", "=", False)],
            order="code ASC",
        )
        departments = self.env["account.analytic.account"].search(
            [("plan_id.code", "=", "departments"), ("parent_id", "=", False)],
            order="code ASC",
        )
        app_lines = self.env["budget.appropriation.line"].search(
            [("budget_type", "=", "revenue")]
        )


        account_map = dict(
            (
                account.id,
                {
                    "id": account.id,
                    "code": account.code,
                    "name": account.name,
                    # { [id]: [balance] }
                    "department": {},
                    "total_balance": 0
                },
            )
            for account in accounts
        )

        lines = []

        for line in app_lines:
            account_id = int(line.account_id.parent_path.split("/")[0])
            dept_id = int(line.department_analytic_id.parent_path.split("/")[0])

            if not account_map[account_id]["department"].get(dept_id):
                account_map[account_id]["department"][dept_id] = 0

            account_map[account_id]["department"][dept_id] += line.balance
            account_map[account_id]["total_balance"] += line.balance

        departments_data = [
            {"id": dept.id, "code": dept.code, "name": dept.name}
            for dept in departments
        ]

        return {
            "data": account_map,
            "departments": departments_data,
            "fiscal_year": {
                "id": fiscal_year.id,
                "name": fiscal_year.name,
            },
        }

    @api.model
    def get_state(self):
        return ["draft", "review", "posted"]

    def _get_fiscal_year(self):
        data = self.env["account.fiscal.year"].search([], order="date_from DESC")
        return [
            dict(
                id=n.id,
                name=n.name,
                date_from=n.date_from,
                date_to=n.date_to,
            )
            for n in data
        ]

    @api.model
    def get_config(self):
        fiscal_years = self._get_fiscal_year()
        return {
            "fiscal_years": fiscal_years,
            "state": ["draft", "review", "posted"],
        }
