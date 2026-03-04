import logging

from odoo import _, http
from odoo.http import request, serialize_exception
from odoo.tools import html_escape, pycompat
from odoo.addons.web.controllers.main import ExcelExport
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BudgetAccount(http.Controller):
    @http.route("/budget/budget_account", type="http", auth="public", website=True)
    def index(self, **kw):
        expense_accounts = request.env["budget.account"].sudo().get_as_flat_list('expense')
        revenue_accounts = request.env["budget.account"].sudo().get_as_flat_list('revenue')

        analytic_plan_activities_plan = request.env.ref('account_analytic_kmitl.analytic_plan_activities')
        analytic_plan_activities = request.env['account.analytic.account'].sudo().get_as_flat_list(analytic_plan_activities_plan.id)

        analytic_plan_departments_plan = request.env.ref('account_analytic_kmitl.analytic_plan_departments')
        analytic_plan_departments = request.env['account.analytic.account'].sudo().get_as_flat_list(analytic_plan_departments_plan.id)

        analytic_plan_funds_plan = request.env.ref('account_analytic_kmitl.analytic_plan_funds')
        analytic_plan_funds = request.env['account.analytic.account'].sudo().get_as_flat_list(analytic_plan_funds_plan.id)

        analytic_plan_sources_plan = request.env.ref('account_analytic_kmitl.analytic_plan_sources')
        analytic_plan_sources = request.env['account.analytic.account'].sudo().get_as_flat_list(analytic_plan_sources_plan.id)

        values = {
            "revenue_accounts": revenue_accounts,
            "expense_accounts": expense_accounts,
            "analytic_plan_activities": analytic_plan_activities,
            "analytic_plan_departments": analytic_plan_departments,
            "analytic_plan_funds": analytic_plan_funds,
            "analytic_plan_sources": analytic_plan_sources,
        }

        return request.render("budget_account_portal.portal_budget_account", values)
