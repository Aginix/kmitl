from odoo import http
from odoo.http import request, route
from odoo.tools import format_amount
import logging

_logger = logging.getLogger(__name__)


class BudgetAppropriation(http.Controller):
    @http.route("/budget_appropriation_portal/objects", type="http", auth="user")
    def list(self, **kw):
        return http.request.render(
            "budget_appropriation.listing",
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
                "budget_appropriation.object",
                {
                    "object": app_id,
                    "report": app_id.get_f4_report_data(),
                    "format_monetary": format_monetary,
                },
            )

        report = request.env['budget.appropriation.f5.report'].get_f5_data_flat(budget_appropriation_id)

        return http.request.render(
            "budget_appropriation.expense",
            {
                "object": app_id,
                "report": report,
                "format_monetary": format_monetary,
            },
        )

    @http.route(
        ["/budget/budget_appropriation/multi/<string:budget_appropriation_ids>"],
        type="http",
        auth="public",
        website=True,
    )
    def object_multi(self, budget_appropriation_ids=None, access_token=None, **kw):
        """
        Display merged F5 report for multiple expense appropriations.

        Args:
            budget_appropriation_ids: Comma-separated IDs (e.g., "1,2,3")
        """
        # Parse comma-separated IDs
        try:
            ids = [int(id_str.strip()) for id_str in budget_appropriation_ids.split(",") if id_str.strip()]
        except ValueError:
            return request.not_found()

        if not ids:
            return request.not_found()

        appropriations = request.env["budget.appropriation"].browse(ids)
        if not appropriations.exists():
            return request.not_found()

        # Only expense type supported for multi-ID
        non_expense = appropriations.filtered(lambda a: a.budget_type != "expense")
        if non_expense:
            return request.not_found()

        first = appropriations[0]

        def format_monetary(number):
            return (
                format_amount(request.env, number, first.currency_id)
                .replace(first.currency_id.symbol, "")
                .strip()
            )

        report = request.env['budget.appropriation.f5.report'].get_f5_data_flat(ids)

        # Check for validation errors
        if report.get("error"):
            _logger.warning("F5 multi-report error: %s", report["error"])
            return request.not_found()

        return http.request.render(
            "budget_appropriation.expense",
            {
                "object": first,
                "objects": appropriations,
                "report": report,
                "format_monetary": format_monetary,
            },
        )

    @http.route(
        ["/budget/budget_appropriation/<int:budget_appropriation_id>/content"],
        type="http",
        auth="public",
        website=True,
    )
    def object_content(self, budget_appropriation_id=None, **kw):
        """Render F5 content only (no portal chrome) for iframe embedding."""
        app_id = request.env["budget.appropriation"].browse(budget_appropriation_id)

        if not app_id.exists() or app_id.budget_type != "expense":
            return request.not_found()

        def format_monetary(number):
            return (
                format_amount(request.env, number, app_id.currency_id)
                .replace(app_id.currency_id.symbol, "")
                .strip()
            )

        report = request.env['budget.appropriation.f5.report'].get_f5_data_flat(budget_appropriation_id)

        return http.request.render(
            "budget_appropriation.expense",
            {
                "object": app_id,
                "report": report,
                "format_monetary": format_monetary,
            },
        )

    @http.route(
        ["/budget/budget_appropriation/multi/<string:budget_appropriation_ids>/content"],
        type="http",
        auth="public",
        website=True,
    )
    def object_multi_content(self, budget_appropriation_ids=None, **kw):
        """Render merged F5 content only (no portal chrome) for iframe embedding."""
        try:
            ids = [int(id_str.strip()) for id_str in budget_appropriation_ids.split(",") if id_str.strip()]
        except ValueError:
            return request.not_found()

        if not ids:
            return request.not_found()

        appropriations = request.env["budget.appropriation"].browse(ids)
        if not appropriations.exists():
            return request.not_found()

        non_expense = appropriations.filtered(lambda a: a.budget_type != "expense")
        if non_expense:
            return request.not_found()

        first = appropriations[0]

        def format_monetary(number):
            return (
                format_amount(request.env, number, first.currency_id)
                .replace(first.currency_id.symbol, "")
                .strip()
            )

        report = request.env['budget.appropriation.f5.report'].get_f5_data_flat(ids)

        if report.get("error"):
            _logger.warning("F5 multi-report content error: %s", report["error"])
            return request.not_found()

        return http.request.render(
            "budget_appropriation.expense",
            {
                "object": first,
                "objects": appropriations,
                "report": report,
                "format_monetary": format_monetary,
            },
        )
