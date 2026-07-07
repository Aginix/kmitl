from odoo import _, api, fields, models


class AccountingKmitlDashboard(models.AbstractModel):
    """Read-only aggregation service for the accounting landing dashboard.

    Powers the KPI launchpad shown as the first page of the Accounting app.

    Cards are returned as a plain ordered list of self-describing dicts so that
    other modules can add their own card simply by inheriting
    ``get_dashboard_data`` and appending to ``data["cards"]`` -- no front-end
    change is required. Each card is::

        {id, title, color, sequence, res_model, domain, count[, amount]}

    ``amount`` is present only for money cards. The front-end sorts by
    ``sequence`` and opens ``res_model`` / ``domain`` on click, so a card's
    number always matches the list it opens.

    Nothing here uses ``sudo``: record rules scope every figure to what the
    current user may see.
    """

    _name = "accounting.kmitl.dashboard"
    _description = "KMITL Accounting Dashboard"

    _UNPAID_STATES = ("not_paid", "partial")

    @api.model
    def _make_card(self, card_id, title, color, sequence, res_model, domain):
        """Build a count-only KPI card.

        Reusable extension point: modules extending the dashboard with a card
        over their own model should call this instead of hand-building the dict.
        """
        return {
            "id": card_id,
            "title": title,
            "color": color,
            "sequence": sequence,
            "res_model": res_model,
            "domain": domain,
            "count": self.env[res_model].search_count(domain),
        }

    @api.model
    def _residual_card(self, card_id, title, color, sequence, domain):
        """``account.move`` card carrying count + summed ``amount_residual``
        (both come from a single ``read_group``)."""
        groups = self.env["account.move"].read_group(
            domain, ["amount_residual:sum"], []
        )
        return {
            "id": card_id,
            "title": title,
            "color": color,
            "sequence": sequence,
            "res_model": "account.move",
            "domain": domain,
            "count": groups[0]["__count"] if groups else 0,
            "amount": (groups[0]["amount_residual"] if groups else 0.0) or 0.0,
        }

    @api.model
    def get_dashboard_data(self):
        """Return ``{"currency_symbol": str, "cards": [card, ...]}``."""
        uid = self.env.uid
        today = fields.Date.context_today(self)

        unpaid_ap = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", self._UNPAID_STATES),
        ]
        unpaid_ar = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", self._UNPAID_STATES),
        ]

        cards = [
            self._make_card(
                "my_drafts",
                _("My draft documents"),
                "secondary",
                10,
                "account.move",
                [("state", "=", "draft"), ("create_uid", "=", uid)],
            ),
            self._make_card(
                "submitted",
                _("Submitted (awaiting posting)"),
                "info",
                20,
                "account.move",
                [("state", "=", "submitted"), ("create_uid", "=", uid)],
            ),
            self._residual_card(
                "unpaid_ap", _("Unpaid vendor bills"), "warning", 30, unpaid_ap
            ),
            self._residual_card(
                "overdue_ap",
                _("Overdue vendor bills"),
                "danger",
                40,
                unpaid_ap + [("invoice_date_due", "<", today)],
            ),
            self._residual_card(
                "unpaid_ar", _("Unpaid customer invoices"), "primary", 50, unpaid_ar
            ),
            self._make_card(
                "exceptions",
                _("Documents with exceptions"),
                "danger",
                60,
                "account.move",
                [("exception_ids", "!=", False), ("ignore_exception", "=", False)],
            ),
        ]

        return {
            "currency_symbol": self.env.company.currency_id.symbol,
            "cards": cards,
        }
