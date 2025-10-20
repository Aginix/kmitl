from odoo import http
from odoo.http import request, route
from odoo.tools import format_amount
import logging

_logger = logging.getLogger(__name__)


class BudgetAppropriation(http.Controller):
    @http.route("/budget_appropriation_portal/objects", type="http", auth="user")
    def list(self, **kw):
        return http.request.render(
            "budget_appropriation_portal.listing",
            {
                "root": "/budget_appropriation_portal",
                "objects": http.request.env["budget.appropriation"].search([]),
            },
        )

    @http.route(
        ["/budget/budget_appropriation/<int:budget_appropriation_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def object(self, budget_appropriation_id=None, access_token=None, **kw):
        app_id = request.env["budget.appropriation"].browse(budget_appropriation_id)

        def format_monetary(number):
            return (
                format_amount(request.env, number, app_id.currency_id)
                .replace(app_id.currency_id.symbol, "")
                .strip()
            )

        if app_id.budget_type == "revenue":
            return http.request.render(
                "budget_appropriation_portal.object",
                {
                    "object": app_id,
                    "report": app_id.get_f4_report_data(),
                    "format_monetary": format_monetary,
                },
            )

        report = request.env['budget.appropriation.f5.report'].get_f5_data_flat(budget_appropriation_id)

        return http.request.render(
            "budget_appropriation_portal.expense",
            {
                "object": app_id,
                "report": report,
                "format_monetary": format_monetary,
            },
        )
