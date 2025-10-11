import logging

from odoo import http, _
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
        values = {"revenue_accounts": revenue_accounts, "expense_accounts": expense_accounts}

        return request.render("budget_account_portal.portal_budget_account", values)
