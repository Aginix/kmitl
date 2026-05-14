import json

from odoo import http
from odoo.http import request


class BudgetAppropriationPortalSummaryController(http.Controller):
    """Public portal page for an interactive budget appropriation overview.

    Independent of the backend dashboard controller; data is provided by
    :class:`~odoo.addons.budget_appropriation_summary_dashboard.models.budget_appropriation_portal_summary.BudgetAppropriationPortalSummary`.
    """

    _FILTER_KEYS = (
        "fiscal_year_id",
        "department_id",
        "source_id",
    )

    def _collect_filters(self, kw):
        return {key: kw.get(key) for key in self._FILTER_KEYS if kw.get(key)}

    @http.route(
        "/budget/appropriation/portal_summary",
        type="http",
        auth="user",
        website=True,
    )
    def portal_summary(self, **kw):
        filters = self._collect_filters(kw)
        payload = request.env["budget.appropriation.portal.summary"].get_summary(
            filters
        )
        return request.render(
            "budget_appropriation_summary_dashboard.portal_summary_page",
            {
                "payload": payload,
                "payload_json": json.dumps(payload),
            },
        )

    @http.route(
        "/budget/appropriation/portal_summary/data",
        type="json",
        auth="user",
    )
    def portal_summary_data(self, **kw):
        filters = self._collect_filters(kw)
        return request.env["budget.appropriation.portal.summary"].get_summary(
            filters
        )
