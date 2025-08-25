# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationReportRevenueOverview(models.AbstractModel):
    _name = _description = "budget.appropriation.report.revenue.overview"

    @api.model
    def get_data(self, filters):
        fiscal_year_id = filters.get("fiscal_year_id", False)
        state = filters.get("state", False)
        source_analytic_id = filters.get("source_analytic_id", False)

        if fiscal_year_id:
            fiscal_year = self.env["account.fiscal.year"].browse(fiscal_year_id)
        else:
            fiscal_year = self.env["account.fiscal.year"].search(
                [], limit=1, order="date_from DESC"
            )
            fiscal_year_id = fiscal_year.id

        accounts = self.env["budget.account"].search(
            [("budget_type", "=", "revenue"), ("parent_id", "=", False)],
            order="code ASC",
        )
        departments = self.env["account.analytic.account"].search(
            [("plan_id.code", "=", "departments"), ("parent_id", "=", False)],
            order="code ASC",
        )

        domain = [("budget_type", "=", "revenue")]
        if state:
            domain.append(("parent_state", "=", state))
        if fiscal_year_id:
            domain.append(("date_range_fy_id", "=", fiscal_year_id))
        if source_analytic_id:
            domain.append(("source_analytic_id", "=", source_analytic_id))
        app_lines = self.env["budget.appropriation.line"].search(domain)

        account_map = dict(
            (
                account.id,
                {
                    "id": account.id,
                    "code": account.code,
                    "name": account.name,
                    # { [id]: [balance] }
                    "department": {},
                    "total_balance": 0,
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

        dept_map = [{"id": n.id, "code": n.code, "name": n.name} for n in departments]
        return {
            "data": account_map,
            "departments": dept_map,
            "fiscal_year": {
                "id": fiscal_year.id,
                "name": fiscal_year.name,
            },
            "filters": {"fiscal_year_id": fiscal_year_id, "state": state},
        }

    def _get_fiscal_year_options(self):
        data = self.env["account.fiscal.year"].search([], order="date_from DESC")
        return [
            dict(
                id=n.id,
                name=n.name,
                date_from=n.date_from.strftime("%Y-%m-%d"),
                date_to=n.date_to.strftime("%Y-%m-%d"),
            )
            for n in data
        ]

    def _get_source_analytics_options(self):
        data = self.env["account.analytic.account"].search(
            [("plan_id.code", "=", "sources")], order="code ASC"
        )
        return [
            dict(id=n.id, code=n.code, name=n.name, complete_name=n.complete_name)
            for n in data
        ]

    @api.model
    def get_filter_options(self):
        return {
            "state": [{"id": "draft"}, {"id": "review"}, {"id": "posted"}],
            "fiscal_years": self._get_fiscal_year_options(),
            "source_analytics": self._get_source_analytics_options(),
        }
