from odoo import _, api, models


class AccountingKmitlDashboard(models.AbstractModel):
    _inherit = "accounting.kmitl.dashboard"

    @api.model
    def get_dashboard_data(self):
        """Add the "disbursement requests awaiting billing" KPI card.

        A request is awaiting billing while it is in the circuit (signed or in
        progress) or finished, and none of its bills is posted yet. It counts
        whichever station holds it, so it also lists the requests still being
        checked, and the ones whose only bill was cancelled.
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
                    ("state", "in", ("signed", "in_progress", "done")),
                    ("settlement_stage", "=", "none"),
                ],
            )
        )
        return data
