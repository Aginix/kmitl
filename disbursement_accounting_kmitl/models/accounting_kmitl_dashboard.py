from odoo import _, api, models


class AccountingKmitlDashboard(models.AbstractModel):
    _inherit = "accounting.kmitl.dashboard"

    @api.model
    def get_dashboard_data(self):
        """Add the "disbursement requests awaiting billing" KPI card.

        A request is awaiting billing while it is in the circuit (signed or in
        progress) and no bill has been raised for it yet. It counts whichever
        station holds it, so it also lists the requests still being checked.
        """
        data = super().get_dashboard_data()
        data["cards"].append(
            self._make_card(
                "disbursement_awaiting_bill",
                _("Disbursement requests awaiting billing"),
                "info",
                25,
                "disbursement.request",
                [
                    ("state", "in", ("signed", "in_progress")),
                    ("settlement_stage", "=", "none"),
                    ("bill_ids", "=", False),
                ],
            )
        )
        return data
