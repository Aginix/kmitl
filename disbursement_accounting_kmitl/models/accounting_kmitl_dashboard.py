from odoo import _, api, models


class AccountingKmitlDashboard(models.AbstractModel):
    _inherit = "accounting.kmitl.dashboard"

    @api.model
    def get_dashboard_data(self):
        """Add the "disbursement requests awaiting billing" KPI card.

        A disbursement request stays ``approved`` until every active bill is
        posted, at which point it advances to ``bills_posted`` (see
        ``account.move._post`` in this module). So ``state == 'approved'`` is
        exactly the accounting team's queue of approved requests that still
        need a bill posted.
        """
        data = super().get_dashboard_data()
        data["cards"].append(
            self._make_card(
                "disbursement_awaiting_bill",
                _("Disbursement requests awaiting billing"),
                "info",
                25,
                "disbursement.request",
                [("state", "=", "approved")],
            )
        )
        return data
