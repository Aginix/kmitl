from odoo import _, api, models


class AccountingKmitlDashboard(models.AbstractModel):
    _inherit = "accounting.kmitl.dashboard"

    @api.model
    def get_dashboard_data(self):
        """Add the "disbursement requests awaiting billing" KPI card.

        A disbursement request stays at the billing station until every active
        bill is posted. So ``station_code == 'bill'`` is exactly the accounting
        team's queue of approved requests that still need a bill posted.
        """
        data = super().get_dashboard_data()
        data["cards"].append(
            self._make_card(
                "disbursement_awaiting_bill",
                _("Disbursement requests awaiting billing"),
                "info",
                25,
                "disbursement.request",
                [("station_code", "=", "bill")],
            )
        )
        return data
