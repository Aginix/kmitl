from odoo import http
from odoo.http import request


class PurchaseRequestDashboardLeadtimeController(http.Controller):
    """Endpoint for the state-transition leadtime treemap.

    Ignores source_id and selected_states on purpose: the treemap is a
    system-wide metric across every PR in the fiscal year, matching the
    original chart's behaviour.
    """

    TRACKED_TRANSITIONS = [
        ("draft", "to_verify", "จัดทำคำขอ"),
        ("to_verify", "to_approve", "จองเงิน"),
        ("to_approve", "approved", "ขออนุมัติคำขอ"),
        ("approved", "in_progress", "จัดซื้อจัดจ้าง"),
        ("in_progress", "done", "จัดทำสัญญา"),
    ]

    @http.route(
        "/purchase_request/dashboard/leadtime_heatmap",
        type="json",
        auth="user",
    )
    def leadtime_heatmap(self, fiscal_year_id=None, **kw):
        res_ids = None
        if fiscal_year_id:
            prs = request.env["purchase.request"].search(
                [("account_fiscal_year_id", "=", fiscal_year_id)]
            )
            res_ids = prs.ids

        log = request.env["state.leadtime.log"].sudo()
        data = []
        for from_state, to_state, label in self.TRACKED_TRANSITIONS:
            stats = log.get_stats(
                res_model="purchase.request",
                from_state=from_state,
                to_state=to_state,
                res_ids=res_ids,
                latest_only=True,
            )
            data.append({
                "name": label,
                "from_state": from_state,
                "to_state": to_state,
                "avg": round(stats["avg_minutes"], 2),
                "total": round(stats["total_minutes"], 2),
                "count": stats["count"],
            })
        return data
